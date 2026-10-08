"""Conftest for xknxproject."""

import json
from pathlib import Path
import zipfile

from xknxproject.models import DeviceInstance, KNXProject, XMLArea, XMLLine

from . import STUBS_PATH


def copy_project_with_member(
    source: Path, target: Path, member: str, content: bytes
) -> Path:
    """Copy a project archive, replacing one member without changing the fixture."""
    with zipfile.ZipFile(source) as original:
        assert member in original.namelist()
        with zipfile.ZipFile(target, "w") as modified:
            for name in original.namelist():
                modified.writestr(
                    name, content if name == member else original.read(name)
                )
    return target


def assert_stub(to_be_verified: KNXProject, stub_name: str) -> None:
    """Assert input matched loaded stub file."""
    stub_path = STUBS_PATH / stub_name

    def remove_xknxproject_version(obj: KNXProject) -> KNXProject:
        """Remove xknxproject_version from object."""
        version_string = obj["info"].pop("xknxproject_version")
        assert len(version_string.split(".")) == 3
        return obj

    with stub_path.open(encoding="utf-8") as stub_file:
        stub = remove_xknxproject_version(json.load(stub_file))
        to_be_verified = remove_xknxproject_version(to_be_verified)
        for key, value in stub.items():
            assert key in to_be_verified, f"`{key}` key missing in generated object"
            assert value == to_be_verified[key], f"`{key}` item does not match"

        for key in to_be_verified:
            assert key in stub, f"`{key}` key of generated object missing in stub"


def build_devices(*instances: tuple[str, int]) -> list[DeviceInstance]:
    """Build devices on line 1.1 from (device instance Id, device address) pairs."""
    area = XMLArea(address=1, name="", description=None, lines=[])
    line = XMLLine(
        address=1, description=None, name="", medium_type="MT-0", devices=[], area=area
    )
    return [
        DeviceInstance(
            identifier=identifier,
            address=address,
            project_uid=None,
            name="",
            description="",
            last_modified=None,
            product_ref="",
            hardware_program_ref="",
            line=line,
            manufacturer="M-0083",
            additional_addresses=[],
            channels=[],
            com_object_instance_refs=[],
            module_instances=[],
            parameter_instance_refs={},
        )
        for identifier, address in instances
    ]
