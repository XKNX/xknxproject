"""Test project loader."""

from __future__ import annotations

from unittest.mock import Mock
from xml.etree import ElementTree

from xknxproject.loader.project_loader import _LocationLoader
from xknxproject.models import DeviceInstance, KNXMasterData, XMLArea, XMLLine
from xknxproject.zip import KNXProjContents

# ETS 6 project schema namespace; the loader matches any namespace (`{*}`)
_NS = "http://knx.org/xml/project/21"


def _devices(*instances: tuple[str, int]) -> list[DeviceInstance]:
    """Build devices on line 1.1 from (device instance Id, device address) pairs."""
    area = XMLArea(address=1, name="", description=None, lines=[])
    line = XMLLine(
        address=1, description=None, name="", medium_type="MT-0", devices=[], area=area
    )
    return [
        DeviceInstance(
            identifier=identifier,
            address=address,
            project_uid=None,
            name="",
            description="",
            last_modified=None,
            product_ref="",
            hardware_program_ref="",
            line=line,
            manufacturer="M-0083",
            additional_addresses=[],
            channels=[],
            com_object_instance_refs=[],
            module_instances=[],
            parameter_instance_refs={},
        )
        for identifier, address in instances
    ]


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
    """Devices map to the space listing them, not its ancestors; unlisted map to None."""
    devices = _devices(("P-1_DI-9", 9), ("P-1_DI-1", 1), ("P-1_DI-5", 5))
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
    devices = _devices(("P-1_DI-1", 1))
    _load_locations(
        f"""
        <Locations xmlns="{_NS}">
          <Space Id="P-1_BP-1" Name="EG" Type="Floor">
            <Space Id="P-1_BP-2" Name="Flur" Type="Corridor">
              <DeviceInstanceRef RefId="P-1_DI-1" />
            </Space>
          </Space>
          <Space Id="P-1_BP-3" Name="Technik" Type="Room">
            <DeviceInstanceRef RefId="P-1_DI-1" />
          </Space>
        </Locations>
        """,
        devices,
    )

    assert devices[0].space_id == "P-1_BP-2"


def test_devices_sharing_an_address_keep_their_own_space() -> None:
    """Devices with the same individual address are told apart by their instance Id."""
    devices = _devices(("P-1_DI-1", 1), ("P-1_DI-2", 1))
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
