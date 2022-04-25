"""Handles Group adresses."""
from __future__ import annotations


class GroupAddress:
    """Class that represents a group address."""

    def __init__(self, name: str, identifier: str, address: str, dpt_type: str | None):
        """Initialize a group address."""
        self.name = name
        self.identifier = identifier
        self.address = int(address)
        self.dpt_type = dpt_type
        self.nice_address = self._parse_address()

    def _parse_address(self) -> str:
        """Parse a given address and returns a string representation of it."""
        main = (self.address & 0b1111100000000000) >> 11
        middle = (self.address & 0b11100000000) >> 8
        sub = self.address & 0b11111111
        return f"{main}/{middle}/{sub}"

    def __repr__(self) -> str:
        """Return string representation."""
        return f"{self.nice_address} ({self.name}) - [DPT: {self.dpt_type}, ID: {self.identifier}]"
