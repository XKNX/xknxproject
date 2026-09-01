"""Test parser."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from xml.etree import ElementTree

import pytest

from xknxproject.loader.project_loader import _TopologyLoader
from xknxproject.models.models import XMLArea, XMLLine
from xknxproject.xml.parser import XMLParser
from xknxproject.zip import KNXProjContents, extract

from .. import RESOURCES_PATH

xknx_test_project_protected_ets5 = RESOURCES_PATH / "xknx_test_project.knxproj"
xknx_test_project_module_defs = RESOURCES_PATH / "module-definition-test.knxproj"
xknx_test_project_ets5 = RESOURCES_PATH / "xknx_test_project_no_password.knxproj"
xknx_test_project_protected_ets6 = RESOURCES_PATH / "testprojekt-ets6.knxproj"


def test_secure_info_is_opt_in() -> None:
    """Parse ETS6 security credentials only when explicitly requested."""
    device_element = ElementTree.fromstring(
        """
        <DeviceInstance xmlns="http://knx.org/xml/project/23"
            Id="P-1_DI-1" Address="1" Puid="1">
          <Security DeviceAuthenticationCode="auth-code"
              DeviceAuthenticationCodeHash="auth-hash"
              DeviceManagementPassword="management-password"
              DeviceManagementPasswordHash="management-hash"
              ToolKey="tool-key" />
          <BusInterfaces>
            <BusInterface RefId="BI-1" Password="bus-password"
                PasswordHash="bus-hash" />
          </BusInterfaces>
        </DeviceInstance>
        """
    )
    area = XMLArea(0, "", None, [])
    line = XMLLine(0, None, "", "", [], area)

    project_contents = cast(KNXProjContents, None)
    default_device = _TopologyLoader(project_contents)._create_device(
        device_element, line
    )
    assert default_device is not None
    assert default_device.secure_info is None

    secure_device = _TopologyLoader(
        project_contents, include_secure_info=True
    )._create_device(device_element, line)
    assert secure_device is not None
    assert secure_device.secure_info is not None
    assert secure_device.secure_info.device_authentication_code == "auth-code"
    assert secure_device.secure_info.device_authentication_code_hash == "auth-hash"
    assert secure_device.secure_info.device_management_password == "management-password"
    assert (
        secure_device.secure_info.device_management_password_hash == "management-hash"
    )
    assert secure_device.secure_info.tool_key == "tool-key"
    assert secure_device.secure_info.bus_interfaces[0].ref_id == "BI-1"
    assert secure_device.secure_info.bus_interfaces[0].password == "bus-password"
    assert secure_device.secure_info.bus_interfaces[0].password_hash == "bus-hash"


def test_parse_project_ets6() -> None:
    """Test parsing of group addresses."""
    with extract(xknx_test_project_protected_ets6, "test") as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 3
    assert parser.group_addresses[0].address == "0/1/0"
    assert parser.group_addresses[1].address == "0/1/1"
    assert parser.group_addresses[2].address == "0/1/2"

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 3
    assert len(parser.areas[1].lines[1].devices[0].additional_addresses) == 4
    # All instantiated communication objects are exposed, including those with no
    # group address links; the subset that carries links stays at 2.
    _device = parser.areas[1].lines[1].devices[1]
    assert len(_device.com_object_instance_refs) == 8
    _linkless = [c for c in _device.com_object_instance_refs if not c.links]
    assert len(_linkless) == 6
    assert sum(bool(c.links) for c in _device.com_object_instance_refs) == 2
    # The kept link-less objects are usable, not just present: each is merged from the
    # application program (com object number and DPT), which is the point of keeping them.
    assert all(c.number is not None for c in _linkless)
    assert all(c.datapoint_types for c in _linkless)
    assert parser.areas[1].lines[1].devices[0].manufacturer_name == "MDT technologies"


def test_parse_project_ets5() -> None:
    """Test parsing of ETS5 project."""
    with extract(xknx_test_project_protected_ets5, "test") as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 19
    parsed_gas = {ga.address for ga in parser.group_addresses}
    assert len(parsed_gas) == len(parser.group_addresses)
    assert parsed_gas == {
        "1/0/0",
        "1/0/1",
        "1/0/2",
        "1/0/3",
        "1/0/4",
        "1/0/5",
        "2/0/0",
        "2/0/1",
        "2/0/6",
        "2/1/1",
        "2/1/2",
        "2/1/10",
        "2/1/21",
        "2/1/22",
        "2/1/23",
        "7/0/0",
        "7/1/0",
        "7/1/1",
        "7/1/2",
    }

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 4
    assert len(parser.areas[1].lines[1].devices[0].additional_addresses) == 4
    assert len(parser.areas[1].lines[1].devices[1].com_object_instance_refs) == 7


@pytest.mark.parametrize(
    ("filename", "password"),
    [
        (RESOURCES_PATH / "test_project-ets4-no_password.knxproj", None),
        (RESOURCES_PATH / "test_project-ets4.knxproj", "test"),
    ],
)
def test_parse_project_ets4(filename: Path, password: str | None) -> None:
    """Test parsing of ETS4 project."""
    with extract(filename, password) as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 3
    parsed_gas = {ga.address for ga in parser.group_addresses}
    assert len(parsed_gas) == len(parser.group_addresses)
    assert parsed_gas == {
        "0/0/1",
        "0/0/2",
        "0/0/3",
    }

    assert len(parser.areas) == 1
    assert len(parser.areas[0].lines) == 1
    assert len(parser.areas[0].lines[0].devices) == 2
    assert parser.areas[0].lines[0].devices[0].manufacturer_name == "MDT technologies"
    assert parser.areas[0].lines[0].devices[1].manufacturer_name == "ABB"

    assert len(parser.devices) == 2
    assert parser.devices[0].individual_address == "0.0.1"
    assert parser.devices[1].individual_address == "0.0.2"


def test_parse_project_with_module_defs() -> None:
    """Test parsing of ETS5 project with module definitions."""
    with extract(xknx_test_project_module_defs) as knx_project_contents:
        parser = XMLParser(knx_project_contents)
        parser.parse()

    assert len(parser.group_addresses) == 25
    assert parser.group_addresses[0].address == "0/0/1"
    assert parser.group_addresses[1].address == "0/0/2"
    assert parser.group_addresses[2].address == "0/0/3"

    assert len(parser.areas) == 2
    assert len(parser.areas[1].lines) == 2
    assert len(parser.areas[1].lines[1].devices) == 4

    assert len(parser.devices) == 4
