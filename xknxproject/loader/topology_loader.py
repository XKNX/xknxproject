"""Group Address Loader."""
from __future__ import annotations

from xml.dom.minidom import Document, parseString

import aiofiles

from xknxproject.models import ComObjectInstanceRef, DeviceInstance, XMLArea, XMLLine
from xknxproject.util import attr, child_nodes

from . import XMLLoader


class TopologyLoader(XMLLoader):
    """Load topology from KNX XML."""

    def __init__(self, project_id: str):
        """Initialize the GroupAddressLoader."""
        self.project_id = project_id

    async def load(self, extraction_path: str) -> list[XMLArea]:
        """Load Hardware mappings."""
        areas: list[XMLArea] = []
        async with aiofiles.open(
            extraction_path + self.project_id + "/0.xml", encoding="utf-8"
        ) as project_xml:
            dom: Document = parseString(await project_xml.read())
            node: Document = dom.getElementsByTagName("Topology")[0]

            for sub_node in child_nodes(node):
                if sub_node.nodeName == "Area":
                    areas.append(TopologyLoader._create_area(sub_node))

        return areas

    @staticmethod
    def _create_area(node: Document) -> XMLArea:
        """Create an Area."""
        address: int = int(attr(node.attributes.get("Address")))
        name: str = attr(node.attributes.get("Name"))
        description: str = attr(node.attributes.get("Description"))
        area: XMLArea = XMLArea(address, name, description, [])

        for sub_node in child_nodes(node):
            if sub_node.nodeName == "Line":
                area.lines.append(TopologyLoader._create_line(sub_node, area))

        return area

    @staticmethod
    def _create_line(node: Document, area: XMLArea) -> XMLLine:
        """Create a Line."""
        attrs = node.attributes
        address: int = int(attr(attrs.get("Address")))
        name: str = attr(attrs.get("Name"))
        description: str = attr(attrs.get("Description"))
        medium_type: str = attr(attrs.get("MediumTypeRefId"))
        line: XMLLine = XMLLine(address, description, name, medium_type, [], area)

        for sub_node in child_nodes(node):
            if sub_node.nodeName == "DeviceInstance":
                device = TopologyLoader._create_device(sub_node, line)
                if device is not None:
                    line.devices.append(device)
            if sub_node.nodeName == "Segment":
                #  ETS-6 had to change the format :-)
                attrs = sub_node.attributes
                _medium_type: str = attr(attrs.get("MediumTypeRefId"))
                line.medium_type = _medium_type
                for sub_sub_node in child_nodes(sub_node):
                    if sub_sub_node.nodeName == "DeviceInstance":
                        device = TopologyLoader._create_device(sub_sub_node, line)
                        if device is not None:
                            line.devices.append(device)

        return line

    @staticmethod
    def _create_device(node: Document, line: XMLLine) -> DeviceInstance | None:
        """Create device."""
        attrs = node.attributes
        identifier: str = attr(attrs.get("Id"))
        address: str | None = attr(attrs.get("Address"))

        #  devices like power supplies do usually not have an IA.
        if address is None:
            return None

        name: str = attr(attrs.get("Name"))
        last_modified: str = attr(attrs.get("LastModified"))
        hardware_parts = attr(attrs.get("Hardware2ProgramRefId")).split("_")
        hardware_program_ref: str = hardware_parts[0] + "_" + hardware_parts[1]
        device: DeviceInstance = DeviceInstance(
            identifier=identifier,
            address=address,
            name=name,
            last_modified=last_modified,
            hardware_program_ref=hardware_program_ref,
            line=line,
            manufacturer=hardware_program_ref.split("_")[0],
        )

        for sub_node in filter(lambda x: x.nodeType != 3, node.childNodes):
            if sub_node.nodeName == "AdditionalAddresses":
                for address_node in child_nodes(sub_node):
                    if address_node.nodeName == "Address":
                        device.add_additional_address(
                            attr(address_node.attributes.get("Address"))
                        )
            if sub_node.nodeName == "ComObjectInstanceRefs":
                for com_object in child_nodes(sub_node):
                    instance = TopologyLoader._create_com_object_instance(com_object)
                    if instance:
                        device.com_object_instance_refs.append(instance)
            if sub_node.nodeName == "ParameterInstanceRefs":
                for param_object in child_nodes(sub_node):
                    if param_object.nodeName == "ParameterInstanceRef":
                        device.application_program_ref = str(
                            attr(param_object.attributes.get("RefId"))
                        ).split("_")[1]
                        break

        return device

    @staticmethod
    def _create_com_object_instance(node: Document) -> ComObjectInstanceRef | None:
        """Create ComObjectInstanceRef."""
        attrs = node.attributes
        ref_id: str = attr(attrs.get("RefId"))
        text: str = attr(attrs.get("Text"))
        dpt_type: str = attr(attrs.get("DatapointType"))
        links: str | None = attr(attrs.get("Links", None))

        if not links:
            return None

        return ComObjectInstanceRef(ref_id, text, links.split(" "), dpt_type)
