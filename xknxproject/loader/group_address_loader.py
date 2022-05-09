"""Group Address Loader."""
from xml.dom.minidom import Document, parseString

import aiofiles

from xknxproject.models import XMLGroupAddress
from xknxproject.util import attr

from .loader import XMLLoader


class GroupAddressLoader(XMLLoader):
    """Load hardware from KNX XML."""

    def __init__(self, project_id: str):
        """Initialize the GroupAddressLoader."""
        self.project_id = project_id

    async def load(self, extraction_path: str) -> list[XMLGroupAddress]:
        """Load Hardware mappings."""
        group_address_list: list[XMLGroupAddress] = []
        async with aiofiles.open(
            extraction_path + self.project_id + "/0.xml", encoding="utf-8"
        ) as project_xml:
            dom: Document = parseString(await project_xml.read())
            nodes: list[Document] = dom.getElementsByTagName("GroupAddress")
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
