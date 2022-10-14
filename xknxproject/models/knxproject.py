"""Define output type for parsed KNX project."""
from __future__ import annotations

from typing import Any, TypedDict


class Flags(TypedDict):
    """Flags for the group addresses and KOs."""

    read: bool
    write: bool
    communication: bool
    transmit: bool
    update: bool
    read_on_init: bool


class CommunicationObject(TypedDict):
    """Communication object dictionary."""

    name: str | None
    device_address: str
    dpt_type: dict[str, int]
    group_address_links: list[str]
    flags: Flags


class Device(TypedDict):
    """Devices dictionary."""

    name: str
    product_name: str
    description: str
    manufacturer_name: str
    individual_address: str
    communication_object_ids: list[str]


class Line(TypedDict):
    """Line typed dict."""

    name: str
    medium_type: str
    description: str | None
    devices: list[str]


class Area(TypedDict):
    """Area typed dict."""

    name: str
    description: str | None
    lines: dict[str, Line]


class GroupAddress(TypedDict):
    """GroupAddress typed dict."""

    name: str
    identifier: str
    raw_address: int
    address: str
    dpt_type: dict[str, int] | None
    communication_object_ids: list[str]
    description: str


class Space(TypedDict):
    """Space typed dict."""

    type: str
    devices: list[str]
    spaces: dict[str, Any]


class KNXProject(TypedDict):
    """KNXProject typed dictionary."""

    version: str
    communication_objects: dict[str, CommunicationObject]
    devices: dict[str, Device]
    topology: dict[str, Area]
    locations: dict[str, Space]
    group_addresses: dict[str, GroupAddress]
