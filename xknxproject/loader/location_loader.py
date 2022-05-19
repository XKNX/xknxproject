"""Location Loader."""
from xml.dom.minidom import Document, parseString

import aiofiles

from xknxproject.models import DeviceInstance, SpaceType, XMLSpace
from xknxproject.util import attr, child_nodes

from .loader import XMLLoader


class LocationLoader(XMLLoader):
    """Load location infos from KNX XML."""

    def __init__(self, project_id: str, devices: list[DeviceInstance]):
        """Initialize the LocationLoader."""
        self.project_id = project_id
        self.devices: dict[str, str] = {}
        for device in devices:
            self.devices[device.identifier] = device.individual_address

    async def load(self, extraction_path: str) -> list[XMLSpace]:
        """Load Location mappings."""
        spaces: list[XMLSpace] = []
        async with aiofiles.open(
            extraction_path + self.project_id + "/0.xml", encoding="utf-8"
        ) as project_xml:
            dom: Document = parseString(await project_xml.read())
            node: Document = dom.getElementsByTagName("Locations")[0]

            for sub_node in child_nodes(node):
                if sub_node.nodeName == "Space":
                    spaces.append(self.parse_space(sub_node))

        return spaces

    def parse_space(self, node: Document) -> XMLSpace:
        """Parse a space from the document."""
        attrs = node.attributes
        name: str = attr(attrs.get("Name"))
        space_type: SpaceType = SpaceType(attr(attrs.get("Type")))

        space: XMLSpace = XMLSpace([], space_type, name, [])

        for sub_node in child_nodes(node):
            if sub_node.nodeName == "Space":
                # recursively call parse space since this can be nested for an unbound time in the XSD
                space.spaces.append(self.parse_space(sub_node))
            if sub_node.nodeName == "DeviceInstanceRef":
                individual_address = self.devices.get(
                    sub_node.attributes.get("RefId").value
                )
                if individual_address:
                    space.devices.append(individual_address)

        return space
