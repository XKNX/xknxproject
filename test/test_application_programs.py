"""Test parsing application program definitions."""

from __future__ import annotations

import json

import pytest

from xknxproject import XKNXProj
from xknxproject.models import (
    ApplicationProgramDefinition,
    ApplicationProgramIdentity,
    ChannelDefinition,
    ModuleDefinition,
    ObjectDefinition,
    ProductInfo,
)

from . import RESOURCES_PATH, STUBS_PATH

# imported by the refresh_stubs helper script - therefore a constant
APPLICATION_PROGRAM_FIXTURES = [
    ("xknx_test_project", "test", None),
    ("test_project-ets4", "test", "de-DE"),
    ("module-definition-test", None, "De"),
    ("smart_linking", "test", "de-DE"),
]

APPLICATION_PROGRAM_STUBS_PATH = STUBS_PATH / "application_programs"


@pytest.mark.parametrize(
    ("file_stem", "password", "language"), APPLICATION_PROGRAM_FIXTURES
)
def test_parse_application_programs(
    file_stem: str, password: str | None, language: str | None
) -> None:
    """Application program definitions match their stubs."""
    knxproj = XKNXProj(
        RESOURCES_PATH / f"{file_stem}.knxproj", password, language=language
    )
    programs = knxproj.parse_application_programs()
    with (APPLICATION_PROGRAM_STUBS_PATH / f"{file_stem}.json").open(
        encoding="utf-8"
    ) as stub_file:
        stub = json.load(stub_file)
    for program in (*stub.values(), *programs.values()):
        version = program.pop("xknxproject_version")
        assert len(version.split(".")) == 3
    assert programs == stub


@pytest.mark.parametrize(
    "file_stem", [fixture[0] for fixture in APPLICATION_PROGRAM_FIXTURES]
)
def test_application_program_stub_keys_match_typed_dicts(file_stem: str) -> None:
    """Stub items carry exactly the keys their TypedDicts declare."""
    with (APPLICATION_PROGRAM_STUBS_PATH / f"{file_stem}.json").open(
        encoding="utf-8"
    ) as stub_file:
        stub = json.load(stub_file)
    assert stub, "stub must contain at least one application program"
    for program in stub.values():
        assert set(program) == set(ApplicationProgramDefinition.__annotations__)
        assert set(program["identity"]) == set(
            ApplicationProgramIdentity.__annotations__
        )
        for product in program["identity"]["products"]:
            assert set(product) == set(ProductInfo.__annotations__)
        for channel in program["channels"].values():
            assert set(channel) == set(ChannelDefinition.__annotations__)
        for module in program["modules"].values():
            assert set(module) == set(ModuleDefinition.__annotations__)
        for obj in program["objects"].values():
            assert set(obj) == set(ObjectDefinition.__annotations__)
