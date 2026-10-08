"""Test project loader."""

from __future__ import annotations

from unittest.mock import Mock
from xml.etree import ElementTree

from xknxproject.loader.project_loader import _LocationLoader
from xknxproject.models import (
    ApplicationProgram,
    DeviceInstance,
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
