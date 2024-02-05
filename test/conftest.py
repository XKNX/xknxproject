"""Conftest for xknxproject."""
import json
from test import STUBS_PATH

from xknxproject.models import KNXProject


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
