"""Conftest for xknxproject."""
import json
from test import STUBS_PATH

from xknxproject.models import KNXProject


def assert_stub(to_be_verified: KNXProject, stub_name: str) -> None:
    """Assert input matched loaded stub file."""
    stub_path = STUBS_PATH / stub_name

    with open(stub_path, encoding="utf-8") as stub_file:
        stub = json.load(stub_file)
        assert stub["topology"] == to_be_verified["topology"]
        assert stub["group_addresses"] == to_be_verified["group_addresses"]
        assert stub["devices"] == to_be_verified["devices"]
