"""Project file loader."""
from __future__ import annotations

from copy import copy

from lxml import etree

from xknxproject.models import (
    ComObjectInstanceRef,
    DeviceInstance,
    SpaceType,
    XMLArea,
    XMLGroupAddress,
    XMLLine,
    XMLSpace,
)
from xknxproject.util import parse_dpt_types
from xknxproject.zip import KNXProjContents


class ProjectLoader:
    """Load Project file."""

    @staticmethod
    def load(
        knx_proj_contents: KNXProjContents,
    ) -> tuple[
        list[XMLGroupAddress], list[XMLArea], list[DeviceInstance], list[XMLSpace]
    ]:
        """Load topology mappings."""
        areas: list[XMLArea] = []
        group_address_list: list[XMLGroupAddress] = []

        with knx_proj_contents.open_project_0() as project_file:
            for _, elem in etree.iterparse(
                project_file, tag=("{*}GroupAddress", "{*}Topology", "{*}Locations")
            ):
                if elem.tag.endswith("GroupAddress"):
                    group_address_list.append(
                        _GroupAddressLoader.load(group_address_element=elem)
                    )
                elif elem.tag.endswith("Topology"):
                    areas = _TopologyLoader.load(topology_element=elem)
                elif elem.tag.endswith("Locations"):
                    _topology_element = copy(elem)
                elem.clear()

        devices = []
        for area in areas:
            for line in area.lines:
                devices.extend(line.devices)
        spaces = _LocationLoader(devices).load(topology_element=_topology_element)

        return group_address_list, areas, devices, spaces


class _GroupAddressLoader:
    """Load GroupAddress info from KNX XML."""

    @staticmethod
    def load(group_address_element: etree.Element) -> XMLGroupAddress:
        """Load GroupAddress mappings."""

        return XMLGroupAddress(
            name=group_address_element.get("Name"),
            identifier=group_address_element.get("Id"),
            address=group_address_element.get("Address"),
            dpt_type=group_address_element.get("DatapointType"),
        )


class _TopologyLoader:
    """Load topology from KNX XML."""

    @staticmethod
    def load(topology_element: etree.Element) -> list[XMLArea]:
        """Load topology mappings."""
        areas: list[XMLArea] = []

        for area in topology_element.findall("{*}Area"):
            areas.append(_TopologyLoader._create_area(area))

        return areas

    @staticmethod
    def _create_area(area_element: etree.Element) -> XMLArea:
        """Create an Area."""
        address: int = int(area_element.get("Address"))
        name: str = area_element.get("Name")
        description: str = area_element.get("Description")
        area: XMLArea = XMLArea(address, name, description, [])

        for line_element in area_element:
            area.lines.append(_TopologyLoader._create_line(line_element, area))

        return area

    @staticmethod
    def _create_line(line_element: etree.Element, area: XMLArea) -> XMLLine:
        """Create a Line."""
        address: int = int(line_element.get("Address"))
        name: str = line_element.get("Name")
        description: str = line_element.get("Description")
        if (segment := line_element.find("{*}Segment")) is not None:
            #  ETS-6 (21) adds "Segment" tags between "Line" and "DeviceInstance" tags
            medium_type = segment.get("MediumTypeRefId")
        else:
            medium_type = line_element.get("MediumTypeRefId")
        line: XMLLine = XMLLine(address, description, name, medium_type, [], area)

        for device_element in line_element.iterdescendants(tag="{*}DeviceInstance"):
            if device := _TopologyLoader._create_device(device_element, line):
                line.devices.append(device)

        return line

    @staticmethod
    def _create_device(
        device_element: etree.Element, line: XMLLine
    ) -> DeviceInstance | None:
        """Create device."""
        identifier: str = device_element.get("Id")
        address: str | None = device_element.get("Address")

        #  devices like power supplies do usually not have an IA.
        if address is None:
            return None

        name: str = device_element.get("Name")
        last_modified: str = device_element.get("LastModified")
        hardware_parts = device_element.get("Hardware2ProgramRefId").split("_")
        hardware_program_ref: str = hardware_parts[0] + "_" + hardware_parts[1]
        device: DeviceInstance = DeviceInstance(
            identifier=identifier,
            address=address,
            name=name,
            last_modified=last_modified,
            hardware_program_ref=hardware_program_ref,
            line=line,
            manufacturer=hardware_parts[0],
        )

        for sub_node in device_element:
            if sub_node.tag.endswith("AdditionalAddresses"):
                for address_node in sub_node:
                    device.add_additional_address(address_node.get("Address"))
            if sub_node.tag.endswith("ComObjectInstanceRefs"):
                for com_object in sub_node:
                    if instance := _TopologyLoader._create_com_object_instance(
                        com_object
                    ):
                        device.com_object_instance_refs.append(instance)
            if sub_node.tag.endswith("ParameterInstanceRefs"):
                if (
                    param_instance_ref := sub_node.find("{*}ParameterInstanceRef")
                ) is not None:
                    device.application_program_ref = param_instance_ref.get(
                        "RefId"
                    ).split("_")[1]

        return device

    @staticmethod
    def _create_com_object_instance(
        com_object: etree.Element,
    ) -> ComObjectInstanceRef | None:
        """Create ComObjectInstanceRef."""
        ref_id: str = com_object.get("RefId")
        text: str = com_object.get("Text")
        dpt_type: str = com_object.get("DatapointType", "")
        links: str | None = com_object.get("Links")

        if not links:
            return None

        return ComObjectInstanceRef(
            ref_id, text, links.split(" "), parse_dpt_types(dpt_type.split(" "))
        )


class _LocationLoader:
    """Load location infos from KNX XML."""

    def __init__(self, devices: list[DeviceInstance]):
        """Initialize the LocationLoader."""
        self.devices: dict[str, str] = {
            device.identifier: device.individual_address for device in devices
        }

    def load(self, topology_element: etree.Element) -> list[XMLSpace]:
        """Load Location mappings."""
        return [
            self.parse_space(space) for space in topology_element.findall("{*}Space")
        ]

    def parse_space(self, node: etree.Element) -> XMLSpace:
        """Parse a space from the document."""
        name: str = node.get("Name")
        space_type = SpaceType(node.get("Type"))
        space: XMLSpace = XMLSpace([], space_type, name, [])

        for sub_node in node:
            if sub_node.tag.endswith("Space"):
                # recursively call parse space since this can be nested for an unbound time in the XSD
                space.spaces.append(self.parse_space(sub_node))
            elif sub_node.tag.endswith("DeviceInstanceRef"):
                if individual_address := self.devices.get(sub_node.get("RefId")):
                    space.devices.append(individual_address)

        return space
