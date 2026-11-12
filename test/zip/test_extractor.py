"""Test reading KNX projects."""

from pathlib import Path
import struct
import zipfile

import pytest
from pytest import raises

from xknxproject.exceptions import InvalidPasswordException, InvalidProjectArchive
from xknxproject.zip import extract
from xknxproject.zip.extractor import _generate_ets6_zip_password

from .. import RESOURCES_PATH

xknx_test_project_protected_ets5 = RESOURCES_PATH / "xknx_test_project.knxproj"
xknx_test_project_ets5 = RESOURCES_PATH / "xknx_test_project_no_password.knxproj"
xknx_test_project_protected_ets6 = RESOURCES_PATH / "testprojekt-ets6.knxproj"
module_definition_test_project = RESOURCES_PATH / "module-definition-test.knxproj"
xknx_test_project_ets4 = RESOURCES_PATH / "test_project-ets4-no_password.knxproj"
xknx_test_project_protected_ets4 = RESOURCES_PATH / "test_project-ets4.knxproj"


def test_extract_knx_project_ets5() -> None:
    """Test reading a KNX ETS5 project without an error."""
    with extract(xknx_test_project_ets5) as knx_project_contents:
        assert knx_project_contents.root.read("P-01D2/project.xml")

    with raises(ValueError):
        knx_project_contents.root.read("P-01D2/project.xml")


def test_extract_protected_knx_project_ets5() -> None:
    """Test reading a KNX ETS5 project without an error."""
    with extract(xknx_test_project_protected_ets5, "test") as knx_project_contents:
        assert knx_project_contents.root.read("P-0242.signature")
        with knx_project_contents.open_project_0() as proj_0:
            assert '<?xml version="1.0" encoding="utf-8"?>' in proj_0.readline().decode(
                "utf-8"
            )

    with raises(ValueError):
        knx_project_contents.root.read("P-0242.signature")


def test_ets6_password_generation() -> None:
    """Test generating ZIP password for ETS6 files."""
    assert (
        _generate_ets6_zip_password("a").decode("utf-8")
        == "+FAwP4iI7/Pu4WB3HdIHbbFmteLahPAVkjJShKeozAA="
    )
    assert (
        _generate_ets6_zip_password("test").decode("utf-8")
        == "2+IIP7ErCPPKxFjJXc59GFx2+w/1VTLHjJ2duc04CYQ="
    )
    assert (
        _generate_ets6_zip_password("Penn¥w1se 🤡").decode("utf-8")
        == "ZjlYlh+eTtoHvFadU7+EKvF4jOdEm7WkP49uanOMMk0="
    )


def test_extract_protected_knx_project_ets6() -> None:
    """Test reading a KNX ETS6 project without an error."""
    with extract(xknx_test_project_protected_ets6, "test") as knx_project_contents:
        assert knx_project_contents.root.read("P-04BF.signature")
        with knx_project_contents.open_project_0() as proj_0:
            assert '<?xml version="1.0" encoding="utf-8"?>' in proj_0.readline().decode(
                "utf-8"
            )

    with raises(ValueError):
        knx_project_contents.root.read("P-04BF.signature")


def test_wrong_password_ets5() -> None:
    """Test reading a KNX ETS5 project with wrong password."""
    with raises(InvalidPasswordException):
        with extract(xknx_test_project_protected_ets5, "wrong") as knx_project_contents:
            with knx_project_contents.open_project_0():
                pass


def test_wrong_password_ets6() -> None:
    """Test reading a KNX ETS6 project with wrong password."""
    with raises(InvalidPasswordException):
        with extract(xknx_test_project_protected_ets6, "wrong") as knx_project_contents:
            with knx_project_contents.open_project_0():
                pass


def test_required_password_ets6() -> None:
    """Test reading a KNX ETS6 project with wrong password."""
    with raises(InvalidPasswordException):
        with extract(xknx_test_project_protected_ets6, "") as knx_project_contents:
            with knx_project_contents.open_project_0():
                pass


def _corrupt_entry(source: Path, entry_name: str, target: Path) -> Path:
    """Write a copy of `source` with the compressed data of one entry scrambled."""
    with zipfile.ZipFile(source) as archive:
        info = archive.getinfo(entry_name)
    raw = bytearray(source.read_bytes())
    offset = info.header_offset
    name_len, extra_len = struct.unpack("<HH", raw[offset + 26 : offset + 30])
    data_start = offset + 30 + name_len + extra_len
    # scramble a run inside the deflate stream, past any encryption header
    scramble_at = data_start + 64
    for index in range(scramble_at, scramble_at + 64):
        raw[index] ^= 0xFF
    target.write_bytes(raw)
    return target


def test_damaged_project_file(tmp_path: Path) -> None:
    """Test reading a project whose contents can not be decompressed."""
    damaged = _corrupt_entry(
        xknx_test_project_ets5, "P-01D2/0.xml", tmp_path / "damaged.knxproj"
    )
    with raises(InvalidProjectArchive):
        with extract(damaged) as knx_project_contents:
            with knx_project_contents.open_project_0() as proj_0:
                proj_0.read()


def test_damaged_protected_project_file(tmp_path: Path) -> None:
    """Test reading a protected project whose contents can not be decompressed."""
    damaged = _corrupt_entry(
        xknx_test_project_protected_ets6, "P-04BF.zip", tmp_path / "damaged.knxproj"
    )
    with raises(InvalidProjectArchive):
        with extract(damaged, "test") as knx_project_contents:
            with knx_project_contents.open_project_0() as proj_0:
                proj_0.read()


def _break_crc(source: Path, entry_name: str, target: Path) -> Path:
    """Write a copy of `source` with one entry's stored CRC-32 replaced."""
    raw = bytearray(source.read_bytes())
    name = entry_name.encode()
    position = 0
    while (position := raw.find(b"PK\x01\x02", position)) != -1:
        name_len = struct.unpack("<H", raw[position + 28 : position + 30])[0]
        if raw[position + 46 : position + 46 + name_len] == name:
            raw[position + 16 : position + 20] = b"\x00\x00\x00\x00"
            break
        position += 4
    else:  # pragma: no cover - guards against a silently useless test
        raise AssertionError(f"{entry_name} not found in central directory")
    target.write_bytes(raw)
    return target


def test_no_zip_file(tmp_path: Path) -> None:
    """Test reading a file that is not a ZIP archive."""
    not_a_project = tmp_path / "not_a_project.knxproj"
    not_a_project.write_bytes(b"this is not a KNX project")
    with raises(InvalidProjectArchive):
        with extract(not_a_project):
            pass


def test_project_file_failing_checksum(tmp_path: Path) -> None:
    """Test reading a project whose contents don't match their checksum."""
    damaged = _break_crc(
        xknx_test_project_ets5, "P-01D2/0.xml", tmp_path / "damaged.knxproj"
    )
    with raises(InvalidProjectArchive):
        with extract(damaged) as knx_project_contents:
            with knx_project_contents.open_project_0() as proj_0:
                proj_0.read()


@pytest.mark.parametrize(
    ("project_path", "password", "expected_names"),
    [
        (xknx_test_project_ets5, None, ["0.xml", "project.xml"]),
        (xknx_test_project_protected_ets5, "test", ["0.xml", "project.xml"]),
        (xknx_test_project_protected_ets6, "test", ["0.xml", "project.xml"]),
        (xknx_test_project_ets4, None, ["0.xml", "Project.xml"]),
        (xknx_test_project_protected_ets4, "test", ["0.xml", "Project.xml"]),
        (
            module_definition_test_project,
            None,
            ["0.xml", "UserFiles", "project.xml"],
        ),
    ],
)
def test_project_path_iterdir(
    project_path: Path, password: str | None, expected_names: list[str]
) -> None:
    """Test listing the project folder, for every archive layout."""
    with extract(project_path, password) as knx_project_contents:
        project = knx_project_contents.project_path
        assert project.is_dir()
        # The order is the one of the archive, which is unspecified.
        assert sorted(child.name for child in project.iterdir()) == expected_names
        with knx_project_contents.open_project_0() as proj_0:
            assert (project / "0.xml").read_bytes() == proj_0.read()


@pytest.mark.parametrize(
    ("project_path", "password"),
    [(xknx_test_project_ets4, None), (xknx_test_project_protected_ets4, "test")],
)
def test_project_path_is_case_sensitive(
    project_path: Path, password: str | None
) -> None:
    """Test that projects of schema version 11 and older name it Project.xml."""
    with extract(project_path, password) as knx_project_contents:
        project = knx_project_contents.project_path
        assert (project / "Project.xml").is_file()
        assert not (project / "project.xml").exists()
        with knx_project_contents.open_project_meta() as meta:
            assert meta.read() == (project / "Project.xml").read_bytes()


def test_project_path_unprotected() -> None:
    """Test that the project folder of an unprotected project is in the root archive."""
    with extract(xknx_test_project_ets5) as knx_project_contents:
        project = knx_project_contents.project_path
        assert str(project) == "P-01D2"
        assert str(project / "0.xml") == "P-01D2/0.xml"
        assert (project / "0.xml").read_bytes() == knx_project_contents.root.read(
            "P-01D2/0.xml"
        )


def test_project_path_subfolder() -> None:
    """Test reading a file from a subfolder of the project folder."""
    with extract(module_definition_test_project) as knx_project_contents:
        user_files = knx_project_contents.project_path / "UserFiles"
        assert user_files.is_dir()
        assert not user_files.is_file()
        (user_file,) = user_files.iterdir()
        assert user_file.name == "M0083-A0096.etsapp"
        assert user_file.is_file()
        assert not user_file.is_dir()
        assert user_file.read_bytes()[:2] == b"PK"


def test_project_path_missing_file() -> None:
    """Test a path to a file that is not in the project folder."""
    with extract(xknx_test_project_ets5) as knx_project_contents:
        missing = knx_project_contents.project_path / "BinaryData" / "missing.dat"
        assert not missing.exists()
        assert list((knx_project_contents.project_path / "BinaryData").iterdir()) == []
        with raises(KeyError):
            missing.open()
