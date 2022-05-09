"""Define output type for parsed KNX project."""
from typing import Optional, TypedDict


class Flags(TypedDict):
    """Flags for the group addresses and KOs."""

    read: bool
    write: bool
    communication: bool
    transmit: bool
    update: bool
    read_on_init: bool


class GroupAddressAssignment(TypedDict):
    """Group address assignments dictionary."""

    co_name: str
    dpt_type: str
    group_address_links: list[str]
    flags: Flags


class Device(TypedDict):
    """Devices dictionary."""

    name: str
    product_name: str
    description: str
    manufacturer_name: str
    individual_address: str
    group_address_assignments: list[GroupAddressAssignment]


class Line(TypedDict):
    """Line typed dict."""

    name: str
    medium_type: str
    description: str
    devices: list[str]


class Area(TypedDict):
    """Area typed dict."""

    name: str
    description: str
    lines: dict[str, Line]


class GroupAddress(TypedDict):
    """GroupAddress typed dict."""

    name: str
    identifier: str
    raw_address: int
    address: str
    dpt_type: Optional[str]


class KNXProject(TypedDict):
    """KNXProject typed dictionary."""

    version: str
    devices: dict[str, Device]
    topology: dict[str, Area]
    group_addresses: dict[str, GroupAddress]
