"""Test parsing application program definitions."""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
import re
import struct
from types import SimpleNamespace
from typing import IO, Any, Literal, cast
from xml.etree import ElementTree
import zipfile

import pytest

from xknxproject import XKNXProj
from xknxproject.exceptions import InvalidProjectArchive, UnexpectedDataError
from xknxproject.loader import (
    ApplicationProgramDefinitionLoader,
    ApplicationProgramLoader,
    LoadedApplicationProgram,
)
from xknxproject.models import (
    ApplicationProgramDefinition,
    ApplicationProgramIdentity,
    ApplicationProgramsInfo,
    ChannelDefinition,
    DeviceInstance,
    ModuleDefinition,
    ObjectDefinition,
    ProductInfo,
)
from xknxproject.util import (
    canonical_application_id,
    instance_definition_id,
    linked_object_definitions,
    object_channel_id,
)
from xknxproject.xml.application_programs import _original_manufacturer_id

from . import RESOURCES_PATH, STUBS_PATH
from .application_program_stubs import (
    SELECTED_APPLICATION_PROGRAMS,
    application_program_stub,
    program_digest,
)
from .conftest import break_crc, copy_project_with_member

# imported by the refresh_stubs helper script - therefore a constant
APPLICATION_PROGRAM_FIXTURES = [
    ("xknx_test_project", "test", None),
    ("test_project-ets4", "test", "de-DE"),
    ("module-definition-test", None, "De"),
    ("smart_linking", "test", "de-DE"),
]

APPLICATION_PROGRAM_STUBS_PATH = STUBS_PATH / "application_programs"


@pytest.mark.parametrize("missing", ["program", "object"])
def test_readme_example_handles_missing_definitions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], missing: str
) -> None:
    """The documented join skips missing definitions and still prints healthy objects."""
    source = RESOURCES_PATH / "xknx_test_project.knxproj"
    application_id = "M-0002_A-A066-14-550B"
    member = f"M-0002/{application_id}.xml"
    with zipfile.ZipFile(source) as archive:
        tree = ElementTree.fromstring(archive.read(member))
    if missing == "program":
        application = tree.find(".//{*}ApplicationProgram")
        assert application is not None
        del application.attrib["Id"]
    else:
        refs = tree.find(".//{*}ComObjectRefs")
        assert refs is not None
        ref = refs.find(f'{{*}}ComObjectRef[@Id="{application_id}_O-40_R-1433"]')
        assert ref is not None
        refs.remove(ref)
    modified = copy_project_with_member(
        source, tmp_path / "missing.knxproj", member, ElementTree.tostring(tree)
    )
    readme = (RESOURCES_PATH.parent.parent / "README.md").read_text(encoding="utf-8")
    example = next(
        block
        for block in re.findall(r"```python\n(.*?)```", readme, re.DOTALL)
        if "linked_object_definitions" in block
    )
    exec(example, {"knxproj": XKNXProj(modified, "test")})
    output = capsys.readouterr().out
    assert "M-000A_A-20E0-21-9997" in output
    assert f"{application_id} O-40_R-1433" not in output
    if missing == "program":
        assert application_id not in output


@pytest.mark.parametrize("language", [None, "de-DE"])
@pytest.mark.parametrize("damage", ["crc", "deflate"])
def test_damaged_catalog_member_is_skipped(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    language: str | None,
    damage: str,
) -> None:
    """An actual ZIP member read failure leaves the five other programs available."""
    source = RESOURCES_PATH / "smart_linking.knxproj"
    application_id = "M-0083_A-00ED-10-33FD"
    member = f"M-0083/{application_id}.xml"
    if damage == "crc":
        modified = break_crc(source, member, tmp_path / "damaged.knxproj")
    else:
        with zipfile.ZipFile(source) as archive:
            content = archive.read(member)
        modified = copy_project_with_member(
            source,
            tmp_path / "damaged.knxproj",
            member,
            content,
            compression=zipfile.ZIP_DEFLATED,
        )
        with zipfile.ZipFile(modified) as archive:
            info = archive.getinfo(member)
        with modified.open("r+b") as stream:
            stream.seek(info.header_offset)
            header = stream.read(30)
            name_len, extra_len = struct.unpack_from("<HH", header, 26)
            stream.seek(info.header_offset + 30 + name_len + extra_len)
            stream.write(b"\x07")  # BFINAL=1 and reserved DEFLATE BTYPE=3
    programs = XKNXProj(modified, "test", language).parse_application_programs()[
        "application_programs"
    ]
    assert set(programs) == {
        "M-00C5_A-0717-11-0D5A",
        "M-00E1_A-2036-40-865C",
        "M-0064_A-5810-12-2E9D",
        "M-0083_A-00F3-10-1728",
        "M-007C_A-001C-14-E802",
    }
    warnings = [
        record for record in caplog.records if record.levelno >= logging.WARNING
    ]
    assert len(warnings) == 1
    assert warnings[0].levelno == logging.WARNING
    assert f"Skipping application program {member}:" in warnings[0].getMessage()
    assert ("BadZipFile" if damage == "crc" else "error(") in warnings[0].getMessage()


@pytest.mark.parametrize("language", [None, "de-DE"])
def test_truncated_catalog_member_is_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, language: str | None
) -> None:
    """A truncated translation tail drops only the affected program."""
    source = RESOURCES_PATH / "module-definition-test.knxproj"
    member = "M-0083/M-0083_A-013A-32-DCC1.xml"
    with zipfile.ZipFile(source) as archive:
        content = archive.read(member)
    cut = content.index(b"</Language>") + len(b"</Language>")
    modified = copy_project_with_member(
        source, tmp_path / "truncated.knxproj", member, content[:cut]
    )
    programs = XKNXProj(modified, language=language).parse_application_programs()[
        "application_programs"
    ]
    assert set(programs) == {"M-0071_A-5531-37-FDF4", "M-0083_A-0153-10-297A-O00EF"}
    assert any(
        record.levelno == logging.WARNING
        and f"Skipping application program {member}:" in record.getMessage()
        and "ParseError" in record.getMessage()
        for record in caplog.records
    )


def test_damaged_project_data_is_not_skipped(tmp_path: Path) -> None:
    """The tolerant catalog loader does not hide corruption of the project itself."""
    modified = break_crc(
        RESOURCES_PATH / "xknx_test_project_no_password.knxproj",
        "P-01D2/0.xml",
        tmp_path / "damaged-project.knxproj",
    )
    with pytest.raises(InvalidProjectArchive):
        XKNXProj(modified).parse_application_programs()


def _load_stub(file_stem: str) -> dict[str, Any]:
    """Load the application program stub of a fixture project."""
    with (APPLICATION_PROGRAM_STUBS_PATH / f"{file_stem}.json").open(
        encoding="utf-8"
    ) as stub_file:
        return cast(dict[str, Any], json.load(stub_file))


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
    result = knxproj.parse_application_programs()
    assert len(result["info"]["xknxproject_version"].split(".")) == 3
    stub = application_program_stub(
        result, SELECTED_APPLICATION_PROGRAMS.get(file_stem, ())
    )
    assert stub == _load_stub(file_stem)


@pytest.mark.parametrize(
    "file_stem", [fixture[0] for fixture in APPLICATION_PROGRAM_FIXTURES]
)
def test_application_program_stub_keys_match_typed_dicts(file_stem: str) -> None:
    """Stub items carry exactly the keys their TypedDicts declare."""
    stub = _load_stub(file_stem)
    digests = stub["digests"]
    assert digests, "stub must contain at least one application program"
    # complete definitions exist for the selected programs only
    assert set(stub["programs"]) == set(
        SELECTED_APPLICATION_PROGRAMS.get(file_stem, ())
    )
    assert set(stub["programs"]) <= set(digests)
    assert set(stub["info"]) == set(ApplicationProgramsInfo.__annotations__) - {
        "xknxproject_version"
    }
    for digest in digests.values():
        assert set(digest) == {
            "identity",
            "channels",
            "modules",
            "objects",
            "channel_independent_objects",
            "sha256",
        }
        assert set(digest["identity"]) == set(
            ApplicationProgramIdentity.__annotations__
        )
        for product in digest["identity"]["products"]:
            assert set(product) == set(ProductInfo.__annotations__)
    for program in stub["programs"].values():
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


def test_digest_detects_changes() -> None:
    """The digest follows the content, not the key order."""
    programs = XKNXProj(
        RESOURCES_PATH / "module-definition-test.knxproj", language="De"
    ).parse_application_programs()["application_programs"]
    program = programs["M-0083_A-013A-32-DCC1"]
    digest = program_digest(program)
    assert digest["objects"] == len(program["objects"])
    assert len(digest["sha256"]) == 64

    changed = copy.deepcopy(program)
    next(iter(changed["objects"].values()))["text"] += " changed"
    assert program_digest(changed)["sha256"] != digest["sha256"]

    reordered = cast(
        ApplicationProgramDefinition, dict(reversed(list(program.items())))
    )
    reordered["objects"] = dict(reversed(list(program["objects"].items())))
    assert program_digest(reordered) == digest


def _resolve(
    program: ApplicationProgramDefinition,
    instance_id: str,
    application_id: str,
    search_id: Literal["CH", "O"],
) -> str:
    """Resolve an instance id of `parse()` to a key of the program definition."""
    definition_id = instance_definition_id(instance_id, application_id, search_id)
    definitions = program["objects"] if search_id == "O" else program["channels"]
    assert definition_id in definitions, instance_id
    return definition_id


@pytest.mark.parametrize(
    ("file_stem", "password", "language"), APPLICATION_PROGRAM_FIXTURES
)
def test_instance_ids_resolve_to_definitions(
    file_stem: str, password: str | None, language: str | None
) -> None:
    """Instance ids of `parse()` map to definitions, and `object_channel_id()` to the instance channel."""
    knxproj = XKNXProj(
        RESOURCES_PATH / f"{file_stem}.knxproj", password, language=language
    )
    project = knxproj.parse()
    programs = knxproj.parse_application_programs()["application_programs"]

    checked_objects = 0
    for co_id, com_object in project["communication_objects"].items():
        if (application := com_object["device_application"]) is None:
            continue
        program = programs[application]
        object_definition = program["objects"][
            _resolve(program, co_id, application, "O")
        ]
        if (instance_channel := com_object["channel"]) is not None:
            assert object_channel_id(program, object_definition) == _resolve(
                program, instance_channel, application, "CH"
            ), co_id
        checked_objects += 1
    assert checked_objects > 0

    for device in project["devices"].values():
        if not device["channels"]:
            continue
        application = device["application"]
        assert application is not None
        for device_channel_id in device["channels"]:
            _resolve(programs[application], device_channel_id, application, "CH")

    for application, definition_ids in linked_object_definitions(project).items():
        assert definition_ids <= set(programs[application]["objects"])


@pytest.mark.parametrize(
    ("file_stem", "language"),
    [
        ("testprojekt-ets6-functions", "De"),
        ("ets6_two_level", "de-DE"),
        ("ets6_free", "de-DE"),
    ],
)
def test_project_without_application_programs(file_stem: str, language: str) -> None:
    """A project without devices using an application program has no definitions."""
    result = XKNXProj(
        RESOURCES_PATH / f"{file_stem}.knxproj", language=language
    ).parse_application_programs()
    assert result["application_programs"] == {}
    assert result["info"]["language_code"] == "de-DE"


def test_language_code_is_the_requested_language() -> None:
    """`language_code` is the project language, also for programs not translated to it."""
    result = XKNXProj(
        RESOURCES_PATH / "test_project-ets4.knxproj", "test", language="de-DE"
    ).parse_application_programs()
    assert result["info"]["language_code"] == "de-DE"
    # this program ships en-US texts only
    program = result["application_programs"]["M-0083_A-0013-11-A9D6"]
    assert program["identity"]["name"] == "Switching, Staircase 20f"


def test_devices_without_application_are_skipped() -> None:
    """Devices without (or with an empty) application program ref are not grouped."""

    class _Device:
        """Stand-in for DeviceInstance with the attributes grouping reads."""

        def __init__(self, application_program_ref: str | None, xml: str) -> None:
            """Initialize with the program ref and the XML path."""
            self.application_program_ref = application_program_ref
            self._xml = xml

        def application_program_xml(self) -> str:
            """Return the application program XML path."""
            return self._xml

    devices = [
        _Device("M-0001_A-0001-01-0001", "M-0001/M-0001_A-0001-01-0001.xml"),
        _Device(None, "None/None.xml"),
        _Device("", "M-0001/.xml"),
        _Device("M-0001_A-0001-01-0001", "M-0001/M-0001_A-0001-01-0001.xml"),
    ]
    grouped = ApplicationProgramLoader.get_application_program_files_for_devices(
        devices  # type: ignore[arg-type]
    )
    assert list(grouped) == ["M-0001/M-0001_A-0001-01-0001.xml"]
    assert len(grouped["M-0001/M-0001_A-0001-01-0001.xml"]) == 2


def test_oem_identity_from_fixture() -> None:
    """OEM programs carry the original manufacturer from the id suffix."""
    programs = XKNXProj(
        RESOURCES_PATH / "xknx_test_project.knxproj", "test"
    ).parse_application_programs()["application_programs"]
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
    ).parse_application_programs()["application_programs"]
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
    ).parse_application_programs()["application_programs"]
    dali = programs["M-0083_A-0153-10-297A-O00EF"]
    assert dali["channels"]["CH-17"]["object_ids"]
    assert dali["channels"]["CH-84"]["object_ids"]
    assert dali["channel_independent_object_ids"] == []
    z70 = programs["M-0071_A-5531-37-FDF4"]
    # MD-4_SM-1 is instantiated in MD-4, which is instantiated in CH-1
    assert "MD-4_SM-1_O-3-0_R-1" in z70["channels"]["CH-1"]["object_ids"]
    assert z70["objects"]["MD-4_SM-1_O-3-0_R-1"]["channel_ids"] == ["CH-1"]


def test_original_manufacturer_id_sources() -> None:
    """The program attribute wins over the id suffix, the id suffix over the hardware."""

    def _devices(*original_manufacturers: str | None) -> list[DeviceInstance]:
        """Return DeviceInstance stand-ins with the given hardware original manufacturers."""
        return [
            cast(DeviceInstance, SimpleNamespace(original_manufacturer=manufacturer))
            for manufacturer in original_manufacturers
        ]

    oem_id = "M-0008_A-20E0-21-9997-O000A"
    plain_id = "M-0008_A-20E0-21-9997"
    hardware = _devices(None, "m-00ef")
    assert _original_manufacturer_id(oem_id, "m-0001", hardware) == "M-0001"
    assert _original_manufacturer_id(oem_id, None, hardware) == "M-000A"
    assert _original_manufacturer_id(plain_id, None, hardware) == "M-00EF"
    assert _original_manufacturer_id(plain_id, None, _devices(None)) is None


@pytest.mark.parametrize(
    ("application_id", "expected"),
    [
        ("M-0008_A-20E0-21-9997-O000A", "M-000A"),
        ("M-0008_A-20E0-21-9997-o000a", "M-000A"),
        # not 4 hex digits - part of the program, no original manufacturer
        ("M-0008_A-20E0-21-9997-OXYZW", None),
        ("M-0083_A-013A-32-DCC1", None),
    ],
)
def test_original_manufacturer_id_suffix(
    application_id: str, expected: str | None
) -> None:
    """The id suffix follows the same rule as `canonical_application_id`."""
    assert _original_manufacturer_id(application_id, None, []) == expected
    canonical = canonical_application_id(application_id, None)
    if expected is None:
        assert canonical == application_id
    else:
        assert canonical.startswith(f"{expected}_A-")


@pytest.mark.parametrize(
    "error",
    [
        UnexpectedDataError("ApplicationProgram element not found"),
        ElementTree.ParseError("not well-formed"),
        KeyError("Id"),
        FileNotFoundError("M-0002/M-0002_A-A066-14-550B.xml"),
    ],
)
def test_unreadable_program_is_skipped(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, error: Exception
) -> None:
    """A program that can not be read is skipped with a warning, the others are parsed."""
    broken_file = "M-0002/M-0002_A-A066-14-550B.xml"
    load = ApplicationProgramDefinitionLoader.load

    def _load(
        application_program_path: zipfile.Path | IO[bytes], language_code: str | None
    ) -> LoadedApplicationProgram:
        """Raise the error for the broken file, load the others."""
        if str(application_program_path).endswith(broken_file):
            raise error
        return load(application_program_path, language_code)

    monkeypatch.setattr(ApplicationProgramDefinitionLoader, "load", _load)
    programs = XKNXProj(
        RESOURCES_PATH / "xknx_test_project.knxproj", "test"
    ).parse_application_programs()["application_programs"]

    assert list(programs) == [
        "M-0083_A-0139-22-F35B-O0072",
        "M-0002_A-A01B-14-1B7C",
        "M-0008_A-20E0-21-9997-O000A",
    ]
    assert [
        (record.levelno, record.getMessage())
        for record in caplog.records
        if record.levelno >= logging.WARNING
    ] == [(logging.WARNING, f"Skipping application program {broken_file}: {error!r}")]
