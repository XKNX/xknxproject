"""Test parsing ETS projects."""

from __future__ import annotations

from collections.abc import Iterator
import json

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
from .conftest import assert_stub

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
