"""Group Address Loader."""
from xml.dom.minidom import Document

from xknxproject.models import XMLGroupAddress
from xknxproject.util import attr


class GroupAddressLoader:
    """Load hardware from KNX XML."""

    def load(self, project_dom: Document) -> list[XMLGroupAddress]:
        """Load Hardware mappings."""
        group_address_list: list[XMLGroupAddress] = []
        nodes: list[Document] = project_dom.getElementsByTagName("GroupAddress")
        for node in nodes:
            group_address_list.append(
                XMLGroupAddress(
                    name=attr(node.attributes.get("Name")),
                    identifier=attr(node.attributes.get("Id")),
                    address=attr(node.attributes.get("Address")),
                    dpt_type=attr(node.attributes.get("DatapointType")),
                )
            )

        return group_address_list
