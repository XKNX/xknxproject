"""Test parsing ETS projects."""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
import re
import zipfile

import pytest

from xknxproject import XKNXProj
from xknxproject.models import KNXProject
from xknxproject.models.knxproject import (
    CommunicationObject,
    Device,
    Function,
    GroupAddress,
    GroupRange,
    ProjectInfo,
    Space,
    TextParameter,
)

from . import RESOURCES_PATH, STUBS_PATH
from .conftest import assert_stub, copy_project_with_member

# imported by the refresh_stubs helper script - therefore a constant
PROJECT_FIXTURES = [
    ("xknx_test_project", "test", None),
    ("test_project-ets4", "test", "de-DE"),
    (
        "module-definition-test",
        None,
        "De",
    ),  # resolves to "de-DE" in parser for knx_master.xml
    (
        "testprojekt-ets6-functions",
        None,
        "De",
    ),  # resolves to "de-DE" in parser for knx_master.xml
    ("ets6_two_level", None, "de-DE"),
    ("ets6_free", None, "de-DE"),
    ("smart_linking", "test", "de-DE"),
]


@pytest.mark.parametrize(("file_stem", "password", "language"), PROJECT_FIXTURES)
def test_parse_project(file_stem: str, password: str, language: str) -> None:
    """Test parsing of various ETS projects (see pytest parameters)."""
    knxproj = XKNXProj(
        RESOURCES_PATH / f"{file_stem}.knxproj", password, language=language
    )
    project = knxproj.parse()
    assert_stub(project, f"{file_stem}.json")


@pytest.mark.parametrize("file_stem", [fixture[0] for fixture in PROJECT_FIXTURES])
def test_stub_keys_match_typed_dicts(file_stem: str) -> None:
    """
    Test the parsed structures carry exactly the keys their types declare.

    Comparing a parse against a stub cannot catch a key written under a name
    the type doesn't declare - both sides come from the parser. Type checking
    doesn't catch it either: a `# type: ignore` on any argument of a multi-line
    TypedDict call suppresses the extra-key error of the whole call. Readers of
    the declared name then silently get nothing.
    """
    with (STUBS_PATH / f"{file_stem}.json").open(encoding="utf-8") as stub_file:
        stub = json.load(stub_file)

    assert set(stub) == set(KNXProject.__annotations__)
    assert set(stub["info"]) == set(ProjectInfo.__annotations__)
    for section, model, nested_key in (
        ("communication_objects", CommunicationObject, None),
        ("devices", Device, None),
        ("group_addresses", GroupAddress, None),
        ("group_ranges", GroupRange, "group_ranges"),
        ("locations", Space, "spaces"),
        ("functions", Function, None),
    ):
        for item in _iter_items(stub[section], nested_key):
            assert set(item) == set(model.__annotations__), (
                f"`{section}` item does not match `{model.__name__}`"
            )
    for com_object in stub["communication_objects"].values():
        if (text_parameter := com_object["text_parameter"]) is not None:
            assert set(text_parameter) == set(TextParameter.__annotations__)


def _iter_items(section: dict, nested_key: str | None) -> Iterator[dict]:
    """Yield the items of a section, descending into nested ones."""
    for item in section.values():
        yield item
        if nested_key is not None:
            yield from _iter_items(item[nested_key], nested_key)


def _replace_once(content: bytes, pattern: bytes, replacement: bytes) -> bytes:
    """Replace a pattern that occurs exactly once."""
    changed, count = re.subn(pattern, replacement, content)
    assert count == 1, pattern
    return changed


def _with_text(
    application: bytes,
    element: str,
    identifier: str,
    text: str,
    german: str | None,
    attribute: str = "Text",
) -> bytes:
    """Set an attribute of a program element and, if given, of its German translation."""
    application = _replace_once(
        application,
        f'(<{element} Id="{identifier}" [^>]*?){attribute}="[^"]*"'.encode(),
        rf'\1{attribute}="{text}"'.encode(),
    )
    if german is None:
        return application
    return _replace_once(
        application,
        f'(<TranslationElement RefId="{identifier}">\\s*'
        f'<Translation AttributeName="{attribute}" )Text="[^"]*"'.encode(),
        rf'\1Text="{german}"'.encode(),
    )


def test_module_arguments_in_texts(tmp_path: Path) -> None:
    """Module arguments are replaced in a text template before its text parameter."""
    source = RESOURCES_PATH / "module-definition-test.knxproj"
    program = "M-0083/M-0083_A-013A-32-DCC1.xml"
    project_member = "P-0810/0.xml"
    with zipfile.ZipFile(source) as archive:
        application = archive.read(program)
        instances = archive.read(project_member)
    # an argument outside and one nested in the default of the text parameter
    application = _with_text(
        application,
        "ComObjectRef",
        "M-0083_A-013A-32-DCC1_MD-2_O-2-1_R-1",
        "Button {{ChNo}}: {{0:Button {{ChNo}}}}",
        "Taster {{ChNo}}: {{0:Taste {{ChNo}}}}",
    )
    application = _with_text(
        application,
        "Channel",
        "M-0083_A-013A-32-DCC1_MD-2_CH-1",
        "Channel {{ChNo}}: {{0:Channel {{ChNo}}}}",
        "Kanal {{ChNo}}: {{0:Kanal {{ChNo}}}}",
    )
    # name and function text of the object, from the program object and its reference
    application = _with_text(
        application,
        "ComObject",
        "M-0083_A-013A-32-DCC1_MD-2_O-2-1",
        "Value {{ChNo}}",
        None,
        attribute="Name",
    )
    application = _replace_once(
        application,
        rb'(<ComObjectRef Id="M-0083_A-013A-32-DCC1_MD-2_O-2-1_R-1" [^>]*?)( TextParameterRefId=)',
        rb'\1 FunctionText="Input {{ChNo}}"\2',
    )
    # device 1.1.1 takes the texts from the program; channel B keeps the default
    for removed in (
        '<ComObjectInstanceRef RefId="MD-2_M-1_MI-1_O-2-1_R-1" Text="Kanal A: Wohnzimmer"',
        '<ComObjectInstanceRef RefId="MD-2_M-2_MI-1_O-2-1_R-1" Text="Kanal B: Küche"',
        '<Node Type="Channel" RefId="MD-2_M-1_MI-1_CH-1" Text="Kanal {{ChNo}}: Wohnzimmer"',
        '<Node Type="Channel" RefId="MD-2_M-2_MI-1_CH-1" Text="Kanal {{ChNo}}: Küche"',
    ):
        instances = _replace_once(
            instances,
            re.escape(removed.encode()),
            removed.rsplit(" Text=", maxsplit=1)[0].encode(),
        )
    instances = _replace_once(
        instances,
        rb'\s*<ParameterInstanceRef RefId="M-0083_A-013A-32-DCC1_MD-2_M-2_MI-1_P-1_R-1"'
        rb' Value="[^"]*" />',
        b"",
    )
    modified = copy_project_with_member(
        source, tmp_path / "program.knxproj", program, application
    )
    modified = copy_project_with_member(
        modified, tmp_path / "texts.knxproj", project_member, instances
    )
    project = XKNXProj(modified, language="De").parse()

    objects = project["communication_objects"]
    assert objects["1.1.1/MD-2_M-1_MI-1_O-2-1_R-1"]["text"] == "Taster A: Wohnzimmer"
    assert objects["1.1.1/MD-2_M-2_MI-1_O-2-1_R-1"]["text"] == "Taster B: Taste B"
    for module, channel in (("M-1", "A"), ("M-2", "B")):
        communication_object = objects[f"1.1.1/MD-2_{module}_MI-1_O-2-1_R-1"]
        assert communication_object["name"] == f"Value {channel}"
        assert communication_object["function_text"] == f"Input {channel}"
    # an instance text of the project stays
    assert objects["1.1.1/MD-2_M-1_MI-1_O-2-2_R-3"]["text"] == "Kanal A: Wohnzimmer"
    channels = project["devices"]["1.1.1"]["channels"]
    assert channels["MD-2_M-1_MI-1_CH-1"]["name"] == "Kanal A: Wohnzimmer"
    assert channels["MD-2_M-2_MI-1_CH-1"]["name"] == "Kanal B: Kanal B"
    assert objects["1.1.1/MD-2_M-1_MI-1_O-2-1_R-1"]["text_parameter"] == {
        "identifier": "MD-2_M-1_MI-1_P-1_R-1",
        "value": "Wohnzimmer",
    }
    assert objects["1.1.1/MD-2_M-2_MI-1_O-2-1_R-1"]["text_parameter"] == {
        "identifier": "MD-2_M-2_MI-1_P-1_R-1",
        "value": None,
    }
    # named for an instance text of the project as well
    assert objects["1.1.1/MD-2_M-1_MI-1_O-2-2_R-3"]["text_parameter"] == {
        "identifier": "MD-2_M-1_MI-1_P-1_R-1",
        "value": "Wohnzimmer",
    }
    assert objects["1.1.1/O-334_R-21"]["text_parameter"] is None


def test_text_parameters_of_a_program_without_channels(tmp_path: Path) -> None:
    """Objects sharing a text parameter carry the same parameter id."""
    source = RESOURCES_PATH / "xknx_test_project.knxproj"
    application_id = "M-0002_A-A066-14-550B"
    program = f"M-0002/{application_id}.xml"
    with zipfile.ZipFile(source) as archive:
        application = archive.read(program)
    for ref, parameter in (
        ("O-40_R-1433", "P-901_R-901"),
        ("O-41_R-1434", "P-901_R-901"),
        ("O-70_R-1505", "P-902_R-902"),
        ("O-71_R-1506", "P-902_R-902"),
    ):
        application = _replace_once(
            application,
            f'<ComObjectRef Id="{application_id}_{ref}"'.encode(),
            f'<ComObjectRef Id="{application_id}_{ref}" '
            f'TextParameterRefId="{application_id}_{parameter}"'.encode(),
        )
    modified = copy_project_with_member(
        source, tmp_path / "channel_less.knxproj", program, application
    )
    project = XKNXProj(modified, "test").parse()
    assert project["devices"]["1.1.5"]["channels"] == {}
    parameters = {
        object_id: com_object["text_parameter"]
        for object_id, com_object in project["communication_objects"].items()
        if com_object["device_address"] == "1.1.5"
    }
    assert parameters == {
        "1.1.5/O-40_R-1433": {"identifier": "P-901_R-901", "value": None},
        "1.1.5/O-41_R-1434": {"identifier": "P-901_R-901", "value": None},
        "1.1.5/O-70_R-1505": {"identifier": "P-902_R-902", "value": None},
        "1.1.5/O-71_R-1506": {"identifier": "P-902_R-902", "value": None},
        "1.1.5/O-100_R-1577": None,
        "1.1.5/O-101_R-1578": None,
        "1.1.5/O-4_R-1417": None,
    }


def test_project_details(tmp_path: Path) -> None:
    """Numbers, comments and descriptions of the project file are exported."""
    source = RESOURCES_PATH / "testprojekt-ets6-functions.knxproj"
    project_member = "P-05C0/0.xml"
    meta_member = "P-05C0/project.xml"
    with zipfile.ZipFile(source) as archive:
        instances = archive.read(project_member)
        meta = archive.read(meta_member)
    meta = _replace_once(
        meta,
        rb'(<ProjectInformation [^>]*?)Comment=""',
        rb'\1ProjectNumber="2023-17" ContractNumber="C-42"'
        rb' ProjectEnd="2023-08-01T00:00:00Z" Comment="Customer project"',
    )
    instances = _replace_once(
        instances,
        rb'(<Function Id="P-05C0-0_F-1" [^>]*?) Puid=',
        rb'\1 Number="F1" Description="Ceiling light"'
        rb' Comment="{\\rtf1\\ansi Dimmed in the evening\\par}" Puid=',
    )
    instances = _replace_once(
        instances,
        rb'(<GroupAddress Id="P-05C0-0_GA-1" [^>]*?) Puid=',
        rb'\1 Central="true" Global="true" Security="Off" Puid=',
    )
    instances = _replace_once(
        instances,
        rb'(<Area Id="P-05C0-0_A-2" [^>]*?) Puid=',
        rb'\1 Comment="Area comment" Puid=',
    )
    instances = _replace_once(
        instances,
        rb'(<Line Id="P-05C0-0_L-3" [^>]*?) Puid=',
        rb'\1 Comment="Line comment" Puid=',
    )
    modified = copy_project_with_member(
        source, tmp_path / "meta.knxproj", meta_member, meta
    )
    modified = copy_project_with_member(
        modified, tmp_path / "details.knxproj", project_member, instances
    )
    project = XKNXProj(modified, language="De").parse()

    info = project["info"]
    assert info["project_number"] == "2023-17"
    assert info["contract_number"] == "C-42"
    assert info["project_start"] == "2023-07-07T12:39:39.0080948Z"
    assert info["project_end"] == "2023-08-01T00:00:00Z"
    assert info["comment"] == "Customer project"

    function = project["functions"]["F-1"]
    assert function["number"] == "F1"
    assert function["description"] == "Ceiling light"
    assert function["comment"] == "Dimmed in the evening\n"

    group_addresses = project["group_addresses"]
    assert group_addresses["0/0/1"]["central"] is True
    assert group_addresses["0/0/1"]["global_"] is True
    assert group_addresses["0/0/1"]["security"] == "Off"
    assert group_addresses["0/0/2"]["central"] is False
    assert group_addresses["0/0/2"]["global_"] is False
    assert group_addresses["0/0/2"]["security"] == "Auto"

    assert project["topology"]["1"]["comment"] == "Area comment"
    assert project["topology"]["1"]["lines"]["1"]["comment"] == "Line comment"
    assert project["topology"]["1"]["lines"]["0"]["comment"] == ""


def test_device_details(tmp_path: Path) -> None:
    """The comment and the IP configuration of devices are exported."""
    source = RESOURCES_PATH / "module-definition-test.knxproj"
    project_member = "P-0810/0.xml"
    with zipfile.ZipFile(source) as archive:
        instances = archive.read(project_member)
    instances = _replace_once(
        instances,
        rb'(<DeviceInstance Id="P-0810-0_DI-1" [^>]*?)Comment=""([^>]*>)',
        rb'\1Comment="Mounted in the cabinet"\2'
        rb'<IPConfig Assign="Fixed" IPAddress="192.168.1.10" SubnetMask="255.255.255.0"'
        rb' DefaultGateway="192.168.1.1" MACAddress="00:24:6D:01:02:03" />',
    )
    instances = _replace_once(
        instances,
        rb'(<DeviceInstance Id="P-0810-0_DI-2" [^>]*>)',
        rb"\1<IPConfig />",
    )
    modified = copy_project_with_member(
        source, tmp_path / "devices.knxproj", project_member, instances
    )
    devices = XKNXProj(modified, language="De").parse()["devices"]

    assert devices["1.1.1"]["comment"] == "Mounted in the cabinet"
    assert devices["1.1.1"]["ip_config"] == {
        "assign": "Fixed",
        "ip_address": "192.168.1.10",
        "subnet_mask": "255.255.255.0",
        "default_gateway": "192.168.1.1",
        "mac_address": "00:24:6D:01:02:03",
    }
    assert devices["1.1.2"]["comment"] == ""
    assert devices["1.1.2"]["ip_config"] == {
        "assign": "Auto",
        "ip_address": None,
        "subnet_mask": None,
        "default_gateway": None,
        "mac_address": None,
    }
    assert devices["1.1.3"]["ip_config"] is None


def test_communication_object_priority(tmp_path: Path) -> None:
    """The priority is taken from the instance, its reference or the object."""
    source = RESOURCES_PATH / "module-definition-test.knxproj"
    program = "M-0083/M-0083_A-013A-32-DCC1.xml"
    project_member = "P-0810/0.xml"
    with zipfile.ZipFile(source) as archive:
        application = archive.read(program)
        instances = archive.read(project_member)
    application = _replace_once(
        application,
        rb'(<ComObject Id="M-0083_A-013A-32-DCC1_O-334" )',
        rb'\1Priority="Alert" ',
    )
    application = _replace_once(
        application,
        rb'(<ComObjectRef Id="M-0083_A-013A-32-DCC1_MD-2_O-2-1_R-1" )',
        rb'\1Priority="High" ',
    )
    instances = _replace_once(
        instances,
        rb'(<ComObjectInstanceRef RefId="MD-2_M-1_MI-1_O-2-1_R-1" )'
        rb'(Text="Kanal A: Wohnzimmer")',
        rb'\1Priority="Low" \2',
    )
    modified = copy_project_with_member(
        source, tmp_path / "program.knxproj", program, application
    )
    modified = copy_project_with_member(
        modified, tmp_path / "priority.knxproj", project_member, instances
    )
    objects = XKNXProj(modified, language="De").parse()["communication_objects"]

    assert objects["1.1.1/O-334_R-21"]["priority"] == "Alert"
    assert objects["1.1.1/MD-2_M-2_MI-1_O-2-1_R-1"]["priority"] == "High"
    assert objects["1.1.1/MD-2_M-1_MI-1_O-2-1_R-1"]["priority"] == "Low"
    assert objects["1.1.1/MD-2_M-1_MI-1_O-2-2_R-3"]["priority"] == "Low"
