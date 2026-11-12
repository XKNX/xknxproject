"""Test project loader."""

from __future__ import annotations

from unittest.mock import Mock
from xml.etree import ElementTree
from zipfile import Path as ZipPath, ZipFile

from xknxproject.loader.application_program_loader import ApplicationProgramLoader
from xknxproject.loader.project_loader import _LocationLoader
from xknxproject.models import (
    Allocator,
    ApplicationProgram,
    DeviceInstance,
    KNXMasterData,
    ModuleDefinitionNumericArg,
    ModuleInstance,
    ModuleInstanceArgument,
)
from xknxproject.zip import KNXProjContents

from . import RESOURCES_PATH
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


def _allocator_application(allocator_modules: int) -> ApplicationProgram:
    return ApplicationProgram(
        com_objects={},
        com_object_refs={},
        allocators={
            "A_L-3": Allocator(identifier="A_L-3", name="ECG_NO", start=1, end=65)
        },
        module_def_arguments={},
        numeric_args={
            "A_MD-1_A-3": ModuleDefinitionNumericArg(
                allocator_ref_id="A_L-3", value=None, base_value=None
            ),
        },
        channels={},
        allocator_modules={"A_L-3": allocator_modules},
    )


def test_module_arguments_from_an_allocator() -> None:
    """Each module instance gets the next `Allocates` values of the allocator."""
    (device,) = build_devices(("P-1_DI-1", 1))
    device.application_program_ref = "A"
    device.module_instances = [
        ModuleInstance(
            identifier=f"MD-1_M-1_MI-{index}",
            ref_id="MD-1_M-1",
            arguments=[_argument("A_MD-1_A-3", "ECG_NO", "L-3")],
        )
        for index in (1, 4)
    ]
    for module_instance in device.module_instances:
        module_instance.arguments[0].allocates = 2
    application = _allocator_application(allocator_modules=1)

    assert device.module_arguments("MD-1_M-1_MI-1_CH-1", application) == {"ECG_NO": "1"}
    assert device.module_arguments("MD-1_M-1_MI-4_PB-1", application) == {"ECG_NO": "7"}


def test_module_arguments_from_an_allocator_of_several_modules() -> None:
    """An allocator shared by several Module elements is not resolved."""
    (device,) = build_devices(("P-1_DI-1", 1))
    device.application_program_ref = "A"
    device.module_instances = [
        ModuleInstance(
            identifier="MD-1_M-1_MI-1",
            ref_id="MD-1_M-1",
            arguments=[_argument("A_MD-1_A-3", "ECG_NO", "L-3")],
        )
    ]
    device.module_instances[0].arguments[0].allocates = 2

    # how ETS numbers instances across the Module elements is unknown
    assert (
        device.module_arguments(
            "MD-1_M-1_MI-1_CH-1", _allocator_application(allocator_modules=12)
        )
        == {}
    )


def test_allocator_modules_are_counted() -> None:
    """The loader counts the Module elements drawing from each allocator."""
    with ZipFile(RESOURCES_PATH / "module-definition-test.knxproj") as archive:
        application = ApplicationProgramLoader.load(
            ZipPath(archive, "M-0071/M-0071_A-5531-37-FDF4.xml"),
            devices=[],
            language_code=None,
        )

    # one Module element per page of controls, all numbered from "Ctrl_num"
    assert application.allocator_modules["M-0071_A-5531-37-FDF4_L-4"] == 12
    assert application.allocator_modules["M-0071_A-5531-37-FDF4_L-9"] == 1


def test_module_arguments_with_the_allocated_number_stored() -> None:
    """A number stored in the instance argument (ETS 6) is used as is."""
    (device,) = build_devices(("P-1_DI-1", 1))
    device.application_program_ref = "A"
    device.module_instances = [
        ModuleInstance(
            identifier="MD-1_M-1_MI-2",
            ref_id="MD-1_M-1",
            arguments=[_argument("A_MD-1_A-3", "ECG_NO", "9")],
        )
    ]

    # also with an allocator shared by several Module elements
    assert device.module_arguments(
        "MD-1_M-1_MI-2_CH-1", _allocator_application(allocator_modules=12)
    ) == {"ECG_NO": "9"}
