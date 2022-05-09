"""Handles Group adresses."""
from __future__ import annotations

import dataclasses


class XMLGroupAddress:
    """Class that represents a group address."""

    def __init__(self, name: str, identifier: str, address: str, dpt_type: str | None):
        """Initialize a group address."""
        self.name = name
        self.identifier = identifier.split("_")[1]
        self.raw_address = int(address)
        self.dpt_type = dpt_type
        self.address = self._parse_address()

    def _parse_address(self) -> str:
        """Parse a given address and returns a string representation of it."""
        main = (self.raw_address & 0b1111100000000000) >> 11
        middle = (self.raw_address & 0b11100000000) >> 8
        sub = self.raw_address & 0b11111111
        return f"{main}/{middle}/{sub}"

    def __repr__(self) -> str:
        """Return string representation."""
        return f"{self.address} ({self.name}) - [DPT: {self.dpt_type}, ID: {self.identifier}]"


@dataclasses.dataclass
class XMLArea:
    """Class that represents a area."""

    address: int
    name: str
    description: str
    lines: list[XMLLine]


@dataclasses.dataclass
class XMLLine:
    """Class that represents a Line."""

    address: int
    description: str
    name: str
    medium_type: str
    devices: list[DeviceInstance]
    area: XMLArea


class DeviceInstance:
    """Class that represents a device instance."""

    def __init__(
        self,
        *,
        identifier: str,
        address: str,
        name: str,
        last_modified: str,
        hardware_program_ref: str,
        line: XMLLine,
        manufacturer: str,
        additional_addresses: list[str] | None = None,
        com_object_instance_refs: list[ComObjectInstanceRef] | None = None,
        com_objects: list[ComObject] | None = None,
    ):
        """Initialize a Device Instance."""
        self.identifier = identifier
        self.address = address
        self.name = name
        self.last_modified = last_modified
        self.hardware_program_ref = hardware_program_ref
        self.line = line
        self.manufacturer = manufacturer
        self.additional_addresses = additional_addresses or []
        self.com_object_instance_refs = com_object_instance_refs or []
        self.com_objects = com_objects or []
        self.application_program_ref: str = ""

        self.individual_address = (
            f"{self.line.area.address}.{self.line.address}.{self.address}"
        )
        self.product_name: str = ""
        self.hardware_name: str = ""

    def add_additional_address(self, address: str) -> None:
        """Add an additional individual address."""
        self.additional_addresses.append(
            f"{self.line.area.address}/{self.line.address}/{address}"
        )

    def add_com_object_id(self, mapping: dict[str, dict[str, str]]) -> None:
        """Add com object id to com object refs."""
        for ref in self.com_object_instance_refs:
            ref.com_object_ref = mapping.get(
                self.manufacturer
                + "_"
                + self.application_program_ref
                + "_"
                + ref.ref_id,
                None,
            )

    def add_com_objects(self, com_objects_lookup_table: dict[str, ComObject]) -> None:
        """Add communication objects to device instance."""
        for ref in self.com_object_instance_refs:
            if ref.com_object_ref is None:
                continue

            if com_object := com_objects_lookup_table.get(
                str(ref.com_object_ref.get("RefId")), None
            ):
                self.com_objects.append(com_object)

    def application_program_xml(self) -> str:
        """Obtain the file name to the application program XML."""
        return (
            self.manufacturer
            + "/"
            + self.manufacturer
            + "_"
            + self.application_program_ref
            + ".xml"
        )


@dataclasses.dataclass
class ComObjectInstanceRef:
    """Class that represents a ComObjectInstanceRef instance."""

    ref_id: str
    text: str
    links: list[str]
    data_point_type: str
    com_object_ref: dict[str, str] | None = None


@dataclasses.dataclass
class ComObject:
    """Class that represents a ComObject instance."""

    identifier: str
    name: str
    text: str
    object_size: str
    read_flag: bool
    write_flag: bool
    communication_flag: bool
    transmit_flag: bool
    update_flag: bool
    read_on_init_flag: bool
    datapoint_types: list[str]


@dataclasses.dataclass
class Hardware:
    """Model a Hardware instance."""

    identifier: str
    name: str
    product_name: str
