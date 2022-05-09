"""Conftest for xknxproject."""
import json
import os


def assert_stub(to_be_verified, stub_name: str) -> None:
    """Assert input matched loaded stub file."""
    stub_path = os.path.join(os.path.dirname(__file__), "resources/stubs/" + stub_name)

    with open(stub_path, encoding="utf-8") as stub_file:
        stub = json.load(stub_file)
        assert stub == to_be_verified
