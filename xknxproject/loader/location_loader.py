"""Location Loader."""
from xml.dom.minidom import Document

from xknxproject.models import DeviceInstance, SpaceType, XMLSpace
from xknxproject.util import attr, child_nodes


class LocationLoader:
    """Load location infos from KNX XML."""

    def __init__(self, devices: list[DeviceInstance]):
        """Initialize the LocationLoader."""
        self.devices: dict[str, str] = {}
        for device in devices:
            self.devices[device.identifier] = device.individual_address

    def load(self, project_dom: Document) -> list[XMLSpace]:
        """Load Location mappings."""
        spaces: list[XMLSpace] = []
        node: Document = project_dom.getElementsByTagName("Locations")[0]

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
