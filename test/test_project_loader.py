"""Test project loader."""

from __future__ import annotations

from unittest.mock import Mock
from xml.etree import ElementTree

import pytest

from xknxproject.loader.project_loader import _LocationLoader, _TopologyLoader
from xknxproject.models import (
    ApplicationProgram,
    DeviceInstance,
    DeviceSecurity,
    KNXMasterData,
    ModuleDefinitionNumericArg,
    ModuleInstance,
    ModuleInstanceArgument,
)
from xknxproject.zip import KNXProjContents

from .conftest import build_devices

# ETS 6 project schema namespace; the loader matches any namespace (`{*}`)
_NS = "http://knx.org/xml/project/21"


def _load_locations(locations_xml: str, devices: list[DeviceInstance]) -> None:
    """Load an ETS 6 `Locations` element, which sets `space_id` of the devices."""
    knx_proj_contents = Mock(spec=KNXProjContents)
    knx_proj_contents.is_ets4_project.return_value = False
    knx_master_data = KNXMasterData(
        function_type_names={},
        manufacturer_names={},
        space_usage_mapping={},
        translations={},
    )
    _LocationLoader(knx_proj_contents, knx_master_data, devices).load(
        ElementTree.fromstring(locations_xml), functions=[]
    )


def test_device_space_id_is_the_listing_space() -> None:
    """Devices map to the space listing them, not its ancestors, or else to None."""
    devices = build_devices(("P-1_DI-9", 9), ("P-1_DI-1", 1), ("P-1_DI-5", 5))
    _load_locations(
        f"""
        <Locations xmlns="{_NS}">
          <Space Id="P-1_BP-1" Name="Haus" Type="Building">
            <DeviceInstanceRef RefId="P-1_DI-9" />
            <Space Id="P-1_BP-2" Name="Küche" Type="Room">
              <DeviceInstanceRef RefId="P-1_DI-1" />
            </Space>
          </Space>
        </Locations>
        """,
        devices,
    )

    assert {device.identifier: device.space_id for device in devices} == {
        "P-1_DI-9": "P-1_BP-1",
        "P-1_DI-1": "P-1_BP-2",
        "P-1_DI-5": None,
    }


def test_device_listed_twice_maps_to_its_first_listing() -> None:
    """A device listed in two spaces maps to the first listing in project file order."""
    devices = build_devices(("P-1_DI-1", 1))
    _load_locations(
        f"""
        <Locations xmlns="{_NS}">
          <Space Id="P-1_BP-1" Name="EG" Type="Floor">
            <Space Id="P-1_BP-2" Name="Flur" Type="Corridor">
              <DeviceInstanceRef RefId="P-1_DI-1" />
            </Space>
          </Space>
          <Space Id="P-1_BP-3" Name="Keller" Type="Room">
            <DeviceInstanceRef RefId="P-1_DI-1" />
          </Space>
        </Locations>
        """,
        devices,
    )

    assert devices[0].space_id == "P-1_BP-2"


def test_devices_sharing_an_address_keep_their_own_space() -> None:
    """Devices with the same individual address are told apart by their instance Id."""
    devices = build_devices(("P-1_DI-1", 1), ("P-1_DI-2", 1))
    _load_locations(
        f"""
        <Locations xmlns="{_NS}">
          <Space Id="P-1_BP-1" Name="Küche" Type="Room">
            <DeviceInstanceRef RefId="P-1_DI-1" />
          </Space>
          <Space Id="P-1_BP-2" Name="Bad" Type="Room">
            <DeviceInstanceRef RefId="P-1_DI-2" />
          </Space>
        </Locations>
        """,
        devices,
    )

    assert [device.space_id for device in devices] == ["P-1_BP-1", "P-1_BP-2"]


def _argument(ref_id: str, name: str, value: str) -> ModuleInstanceArgument:
    return ModuleInstanceArgument(ref_id=ref_id, value=value, name=name)


def test_module_arguments_of_an_instance() -> None:
    """Literal arguments apply, sub-modules override, computed ones are left out."""
    (device,) = build_devices(("P-1_DI-1", 1))
    device.module_instances = [
        ModuleInstance(
            identifier="MD-4_M-15_MI-1",
            ref_id="MD-4_M-15",
            arguments=[
                _argument("A_MD-4_A-1", "PageNum", "L-9"),
                _argument("A_MD-4_A-5", "ChNo", "A"),
                _argument("A_MD-4_A-6", "Group", "1"),
            ],
        ),
        ModuleInstance(
            identifier="MD-4_M-15_MI-1_SM-1_M-1_MI-1-1-1",
            ref_id="MD-4_SM-1_M-1",
            arguments=[
                _argument("A_MD-4_SM-1_A-1", "DevNum", "MD-4_L-1"),
                _argument("A_MD-4_SM-1_A-4", "Group", "2"),
                _argument("A_MD-4_SM-1_A-5", "ChNo", "B"),
            ],
        ),
        ModuleInstance(identifier="MD-4_M-15_MI-10", ref_id="MD-4_M-15", arguments=[]),
    ]
    application = ApplicationProgram(
        com_objects={},
        com_object_refs={},
        allocators={},
        module_def_arguments={},
        numeric_args={
            "A_MD-4_A-1": ModuleDefinitionNumericArg(
                allocator_ref_id="A_L-9", value=None, base_value=None
            ),
            "A_MD-4_SM-1_A-1": ModuleDefinitionNumericArg(
                allocator_ref_id="A_MD-4_L-1", value=None, base_value=None
            ),
            "A_MD-4_SM-1_A-4": ModuleDefinitionNumericArg(
                allocator_ref_id=None, value=0, base_value="A_MD-4_A-6"
            ),
        },
        channels={},
    )

    # the sub-module's literal ChNo wins, its computed Group hides the base value
    assert device.module_arguments(
        "MD-4_M-15_MI-1_SM-1_M-1_MI-1-1-1_SM-1_O-3-1_R-2", application
    ) == {"ChNo": "B"}
    assert device.module_arguments("MD-4_M-15_MI-1_CH-1", application) == {
        "ChNo": "A",
        "Group": "1",
    }
    assert device.module_arguments("O-334_R-21", application) == {}


def _device_security(device_children: str) -> DeviceSecurity | None:
    """Load the security data of an ETS 6 `DeviceInstance` with the given children."""
    return _TopologyLoader._create_security(  # pylint: disable=protected-access
        ElementTree.fromstring(
            f'<DeviceInstance xmlns="{_NS}" Id="P-1_DI-1" Address="1">'
            f"{device_children}</DeviceInstance>"
        )
    )


def test_device_security() -> None:
    """Keys, passwords and the sequence number are read; hashes are left out."""
    assert _device_security(
        """
        <Security ToolKey="1qyNXOniHEoF1EaeGm9O1Q==" LoadedToolKey="/UzpUMEBmHLsvvQC9He8/w=="
          SequenceNumber="1234" SequenceNumberTimestamp="2024-05-01T10:00:00Z"
          DeviceAuthenticationCode="authcode" DeviceAuthenticationCodeHash="2W7vedSbsgBROAkSj5XhEg=="
          DeviceManagementPassword="test1234" DeviceManagementPasswordHash="hVH0H6qL7jwBo8nJHdnx7g==" />
        <BusInterfaces>
          <BusInterface RefId="M-0083_A-0139-22-F35B-O0072_BI-1" Password="s86;7DI9"
            PasswordHash="X8G1lwCTHbSC4pt5/BmmDg==" />
          <BusInterface RefId="M-0083_A-0139-22-F35B-O0072_BI-2" Name="no password" />
        </BusInterfaces>
        """
    ) == DeviceSecurity(
        tool_key="1qyNXOniHEoF1EaeGm9O1Q==",
        loaded_tool_key="/UzpUMEBmHLsvvQC9He8/w==",
        sequence_number=1234,
        sequence_number_timestamp="2024-05-01T10:00:00Z",
        device_authentication_code="authcode",
        device_management_password="test1234",
        # keyed by the full RefId until the application program is known
        bus_interface_passwords={"M-0083_A-0139-22-F35B-O0072_BI-1": "s86;7DI9"},
    )


def test_device_security_of_bus_interfaces_only() -> None:
    """Bus interface passwords make security data also without a `Security` element."""
    assert _device_security(
        '<BusInterfaces><BusInterface RefId="A-1_BI-1" Password="tunnel1" />'
        "</BusInterfaces>"
    ) == DeviceSecurity(
        tool_key=None,
        loaded_tool_key=None,
        sequence_number=None,
        sequence_number_timestamp=None,
        device_authentication_code=None,
        device_management_password=None,
        bus_interface_passwords={"A-1_BI-1": "tunnel1"},
    )


def test_device_security_sequence_number_zero() -> None:
    """A sequence number of 0 is data."""
    security = _device_security('<Security SequenceNumber="0" />')
    assert security is not None
    assert security["sequence_number"] == 0


@pytest.mark.parametrize(
    "device_children",
    [
        "",
        # projects exported without a password keep empty elements
        '<Security /><BusInterfaces><BusInterface RefId="A-1_BI-1" /></BusInterfaces>',
        '<Security DeviceAuthenticationCodeHash="2W7vedSbsgBROAkSj5XhEg==" />',
        '<Security ToolKey="" />',
    ],
)
def test_device_without_security(device_children: str) -> None:
    """A device without keys, passwords or a sequence number has no security data."""
    assert _device_security(device_children) is None
