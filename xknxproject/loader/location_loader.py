"""Location Loader."""
from lxml import etree

from xknxproject.models import DeviceInstance, SpaceType, XMLSpace
from xknxproject.zip import KNXProjContents


class LocationLoader:
    """Load location infos from KNX XML."""

    def __init__(self, devices: list[DeviceInstance]):
        """Initialize the LocationLoader."""
        self.devices: dict[str, str] = {
            device.identifier: device.individual_address for device in devices
        }

    def load(self, knx_proj_contents: KNXProjContents) -> list[XMLSpace]:
        """Load Location mappings."""
        spaces: list[XMLSpace] = []

        with knx_proj_contents.open_project_0() as project_file:
            for _, elem in etree.iterparse(project_file, tag="{*}Locations"):
                for space in elem.findall("{*}Space"):
                    spaces.append(self.parse_space(space))
                elem.clear()

        return spaces

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
