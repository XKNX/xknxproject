"""Test internal model behavior."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from xknxproject.models.models import XMLGroupAddress, XMLGroupRange


@pytest.mark.parametrize(
    ("formatter", "expected"),
    [
        (lambda: XMLGroupAddress.str_address(1, "invalid"), "GroupAddressStyle"),
        (
            lambda: XMLGroupRange("range", 1, 2, [], [], "", "invalid").str_address(),
            "GroupAddressStyle",
        ),
    ],
)
def test_invalid_group_address_style_error(
    formatter: Callable[[], object], expected: str
) -> None:
    """Explain which group-address style value is invalid."""
    with pytest.raises(ValueError, match=expected):
        formatter()
