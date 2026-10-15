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
    ("project_path", "password", "expected_files"),
    [
        (xknx_test_project_ets5, None, ["project.xml", "0.xml"]),
        (xknx_test_project_protected_ets5, "test", ["project.xml", "0.xml"]),
        (xknx_test_project_protected_ets6, "test", ["0.xml", "project.xml"]),
        (
            module_definition_test_project,
            None,
            ["UserFiles/M0083-A0096.etsapp", "project.xml", "0.xml"],
        ),
    ],
)
def test_list_project_files(
    project_path: Path, password: str | None, expected_files: list[str]
) -> None:
    """Test listing the files of the project folder."""
    with extract(project_path, password) as knx_project_contents:
        assert knx_project_contents.list_project_files() == expected_files


def test_open_project_file() -> None:
    """Test reading files of an unprotected project folder."""
    with extract(xknx_test_project_ets5) as knx_project_contents:
        with knx_project_contents.open_project_file("0.xml") as proj_0:
            assert proj_0.read() == knx_project_contents.root.read("P-01D2/0.xml")
        with knx_project_contents.open_project_file("project.xml") as project:
            assert project.read() == knx_project_contents.root.read(
                "P-01D2/project.xml"
            )


def test_open_project_file_in_subfolder() -> None:
    """Test reading a file from a subfolder of the project folder."""
    with extract(module_definition_test_project) as knx_project_contents:
        with knx_project_contents.open_project_file(
            "UserFiles/M0083-A0096.etsapp"
        ) as user_file:
            assert user_file.read(2) == b"PK"


@pytest.mark.parametrize(
    "project_path", [xknx_test_project_protected_ets5, xknx_test_project_protected_ets6]
)
def test_open_protected_project_file(project_path: Path) -> None:
    """Test reading every file of a password protected project folder."""
    with extract(project_path, "test") as knx_project_contents:
        for name in knx_project_contents.list_project_files():
            with knx_project_contents.open_project_file(name) as project_file:
                assert b"<?xml" in project_file.readline()
        with knx_project_contents.open_project_file("0.xml") as proj_0:
            with knx_project_contents.open_project_0() as expected:
                assert proj_0.read() == expected.read()


def test_open_missing_project_file() -> None:
    """Test opening a file that is not in the project folder."""
    with extract(xknx_test_project_ets5) as knx_project_contents:
        with raises(KeyError):
            knx_project_contents.open_project_file("BinaryData/missing.dat")


@pytest.mark.parametrize(
    "name",
    [
        "",
        "/0.xml",
        "./0.xml",
        "../knx_master.xml",
        "../P-01D2.signature",
        "BinaryData/../../knx_master.xml",
        "BinaryData//0.xml",
        "BinaryData/",
    ],
)
def test_open_project_file_outside_project_folder(name: str) -> None:
    """Test rejecting names that don't point inside the project folder."""
    with extract(xknx_test_project_ets5) as knx_project_contents:
        with raises(ValueError):
            knx_project_contents.open_project_file(name)
