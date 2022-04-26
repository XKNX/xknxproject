"""Handles Group adresses."""
from __future__ import annotations

import dataclasses
from xml.dom.minidom import Document

from .util import attr


class GroupAddress:
    """Class that represents a group address."""

    def __init__(self, name: str, identifier: str, address: str, dpt_type: str | None):
        """Initialize a group address."""
        self.name = name
        self.identifier = identifier
        self._address = int(address)
        self.dpt_type = dpt_type
        self.address = self._parse_address()

    def _parse_address(self) -> str:
        """Parse a given address and returns a string representation of it."""
        main = (self._address & 0b1111100000000000) >> 11
        middle = (self._address & 0b11100000000) >> 8
        sub = self._address & 0b11111111
        return f"{main}/{middle}/{sub}"

    def __repr__(self) -> str:
        """Return string representation."""
        return f"{self.address} ({self.name}) - [DPT: {self.dpt_type}, ID: {self.identifier}]"


@dataclasses.dataclass
class Area:
    """Class that represents a area."""

    address: str
    lines: list[Line]

    @staticmethod
    def from_xml(node: Document) -> Area:
        """Create an area from XML."""
        address: str = attr(node.attributes.get("Address"))
        area: Area = Area(address, [])

        for sub_node in filter(lambda x: x.nodeType != 3, node.childNodes):
            if sub_node.nodeName == "Line":
                line: Line = Line.from_xml(sub_node, area)
                area.lines.append(line)

        return area


@dataclasses.dataclass
class Line:
    """Class that represents a Line."""

    address: str
    name: str
    medium_type: str
    devices: list[DeviceInstance]
    area: Area

    @staticmethod
    def from_xml(node: Document, area: Area) -> Line:
        """Create a line from XML."""
        attrs = node.attributes
        address: str = attr(attrs.get("Address"))
        name: str = attr(attrs.get("Name"))
        medium_type: str = attr(attrs.get("MediumTypeRefId"))
        line: Line = Line(address, name, medium_type, [], area)

        for sub_node in filter(lambda x: x.nodeType != 3, node.childNodes):
            if sub_node.nodeName == "DeviceInstance":
                device = DeviceInstance.from_xml(sub_node, line)
                line.devices.append(device)
            if sub_node.nodeName == "Segment":
                #  ETS-6 had to change the format :-)
                attrs = sub_node.attributes
                _medium_type: str = attr(attrs.get("MediumTypeRefId"))
                line.medium_type = _medium_type
                for sub_sub_node in filter(
                    lambda x: x.nodeType != 3, sub_node.childNodes
                ):
                    if sub_sub_node.nodeName == "DeviceInstance":
                        device = DeviceInstance.from_xml(sub_sub_node, line)
                        line.devices.append(device)

        return line


@dataclasses.dataclass
class DeviceInstance:
    """Class that represents a device instance."""

    address: str
    name: str
    last_modified: str
    hardware_program_ref: str
    line: Line
    additional_addresses: list[str]
    com_object_instance_refs: list[ComObjectInstanceRef]

    def __post_init__(self) -> None:
        """Post initialization."""
        self.individual_address = (
            f"{self.line.area.address}/{self.line.address}/{self.address}"
        )

    def add_additional_address(self, address: str) -> None:
        """Add an additional individual address."""
        self.additional_addresses.append(
            f"{self.line.area.address}/{self.line.address}/{address}"
        )

    @staticmethod
    def from_xml(node: Document, line: Line) -> DeviceInstance:
        """Create an area from XML."""
        attrs = node.attributes
        address: str = attr(attrs.get("Address"))
        name: str = attr(attrs.get("Name"))
        last_modified: str = attr(attrs.get("LastModified"))
        hardware_program_ref: str = attr(attrs.get("Hardware2ProgramRefId"))
        device: DeviceInstance = DeviceInstance(
            address=address,
            name=name,
            last_modified=last_modified,
            hardware_program_ref=hardware_program_ref,
            line=line,
            additional_addresses=[],
            com_object_instance_refs=[],
        )

        for sub_node in filter(lambda x: x.nodeType != 3, node.childNodes):
            if sub_node.nodeName == "AdditionalAddresses":
                for address_node in filter(
                    lambda x: x.nodeType != 3, sub_node.childNodes
                ):
                    if address_node.nodeName == "Address":
                        device.add_additional_address(
                            attr(address_node.attributes.get("Address"))
                        )
            if sub_node.nodeName == "ComObjectInstanceRefs":
                for com_object in filter(
                    lambda x: x.nodeType != 3, sub_node.childNodes
                ):
                    device.com_object_instance_refs.append(
                        ComObjectInstanceRef.from_xml(com_object)
                    )

        return device


@dataclasses.dataclass
class ComObjectInstanceRef:
    """Class that represents a ComObjectInstanceRef instance."""

    ref_id: str
    text: str
    links: list[str]
    data_point_type: str

    @staticmethod
    def from_xml(node: Document) -> ComObjectInstanceRef:
        """Create an ComObjectInstanceRef from XML."""
        attrs = node.attributes
        ref_id: str = attr(attrs.get("RefId"))
        text: str = attr(attrs.get("Text"))
        dpt_type: str = attr(attrs.get("DatapointType"))
        links = attr(attrs.get("Links", ""))
        return ComObjectInstanceRef(ref_id, text, links.split(","), dpt_type)
