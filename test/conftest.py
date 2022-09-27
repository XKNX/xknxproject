"""Conftest for xknxproject."""
import json
from test import STUBS_PATH

from xknxproject.models import KNXProject


def assert_stub(to_be_verified: KNXProject, stub_name: str) -> None:
    """Assert input matched loaded stub file."""
    stub_path = STUBS_PATH / stub_name

    with open(stub_path, encoding="utf-8") as stub_file:
        stub = json.load(stub_file)
        for key, value in stub.items():
            assert key in to_be_verified, f"`{key}` key missing in generated object"
            assert value == to_be_verified[key], f"`{key}` item does not match"

        for key in to_be_verified.keys():
            assert key in stub, f"`{key}` key of generated object missing in stub"
