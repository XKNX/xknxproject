"""Group Address Loader."""
from __future__ import annotations

from lxml import etree

from xknxproject.models import ComObjectInstanceRef, DeviceInstance, XMLArea, XMLLine
from xknxproject.util import parse_dpt_types
from xknxproject.zip import KNXProjContents


class TopologyLoader:
    """Load topology from KNX XML."""

    def load(self, knx_proj_contents: KNXProjContents) -> list[XMLArea]:
        """Load topology mappings."""
        areas: list[XMLArea] = []

        with knx_proj_contents.open_project_0() as project_file:
            for _, elem in etree.iterparse(project_file, tag="{*}Topology"):
                for area in elem.findall("{*}Area"):
                    areas.append(TopologyLoader._create_area(area))
                elem.clear()

        return areas

    @staticmethod
    def _create_area(area_element: etree.Element) -> XMLArea:
        """Create an Area."""
        address: int = int(area_element.get("Address"))
        name: str = area_element.get("Name")
        description: str = area_element.get("Description")
        area: XMLArea = XMLArea(address, name, description, [])

        for line_element in area_element:
            area.lines.append(TopologyLoader._create_line(line_element, area))

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
            if device := TopologyLoader._create_device(device_element, line):
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
                    if instance := TopologyLoader._create_com_object_instance(
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
