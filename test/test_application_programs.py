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


def test_devices_without_application_are_skipped() -> None:
    """Devices whose application program can not be resolved are ignored."""
    from xknxproject.xml.application_programs import _group_devices_by_application

    class _Device:
        def __init__(self, application_program_ref: str | None, xml: str) -> None:
            self.application_program_ref = application_program_ref
            self._xml = xml

        def application_program_xml(self) -> str:
            return self._xml

    devices = [
        _Device("M-0001_A-0001-01-0001", "M-0001/M-0001_A-0001-01-0001.xml"),
        _Device(None, "None/None.xml"),
        _Device("M-0001_A-0001-01-0001", "M-0001/M-0001_A-0001-01-0001.xml"),
    ]
    grouped = _group_devices_by_application(devices)  # type: ignore[arg-type]
    assert list(grouped) == ["M-0001/M-0001_A-0001-01-0001.xml"]
    assert len(grouped["M-0001/M-0001_A-0001-01-0001.xml"]) == 2


def test_oem_identity_from_fixture() -> None:
    """OEM programs carry the original manufacturer from the id suffix."""
    programs = XKNXProj(
        RESOURCES_PATH / "xknx_test_project.knxproj", "test"
    ).parse_application_programs()
    identity = programs["M-0008_A-20E0-21-9997-O000A"]["identity"]
    assert identity["manufacturer_id"] == "M-0008"
    assert identity["original_manufacturer_id"] == "M-000A"
    assert identity["application_number"] == 8416
    assert identity["application_version"] == 33
    assert identity["products"], "products using the program are listed"
    assert identity["products"][0]["hardware_id"].startswith("M-0008_H-")


def test_smart_linking_semantics_and_unlinked_objects() -> None:
    """KIM tags are exported and objects without project links are included."""
    programs = XKNXProj(
        RESOURCES_PATH / "smart_linking.knxproj", "test", language="de-DE"
    ).parse_application_programs()
    program = programs["M-00E1_A-2036-40-865C"]
    assert program["identity"]["kim_version"] == "109.77"
    assert program["channels"]["CH-1"]["functional_blocks"] == ["417"]
    assert program["objects"]["O-0_R-1"]["dpas"] == ["417.52"]
    # the project links only a few objects - the definition carries all of them
    assert len(program["objects"]) > 30


def test_modules_instantiated_in_channels_are_channel_members() -> None:
    """Objects of a module instantiated inside a channel belong to that channel."""
    programs = XKNXProj(
        RESOURCES_PATH / "module-definition-test.knxproj", language="De"
    ).parse_application_programs()
    dali = programs["M-0083_A-0153-10-297A-O00EF"]
    assert dali["channels"]["CH-17"]["object_ids"]
    assert dali["channels"]["CH-84"]["object_ids"]
    assert dali["channel_independent_object_ids"] == []
    z70 = programs["M-0071_A-5531-37-FDF4"]
    # MD-4_SM-1 is instantiated in MD-4, which is instantiated in CH-1
    assert "MD-4_SM-1_O-3-0_R-1" in z70["channels"]["CH-1"]["object_ids"]
    assert z70["objects"]["MD-4_SM-1_O-3-0_R-1"]["channel_ids"] == ["CH-1"]
