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
