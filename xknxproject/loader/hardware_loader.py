"""Hardware Loader."""
from pathlib import Path
from typing import Iterator
from xml.dom.minidom import Document, parseString

import aiofiles

from xknxproject.models import Hardware
from xknxproject.util import attr, child_nodes

from .loader import XMLLoader


class HardwareLoader(XMLLoader):
    """Load hardware from KNX XML."""

    async def load(self, extraction_path: Path) -> list[Hardware]:
        """Load Hardware mappings."""
        hardware_list: list[Hardware] = []
        for file in self._get_relevant_files(extraction_path):
            async with aiofiles.open(file, encoding="utf-8") as hardware_xml:
                dom: Document = parseString(await hardware_xml.read())
                node: Document = dom.getElementsByTagName("Manufacturer")[0]

                for sub_node in child_nodes(node):
                    if sub_node.nodeName == "Hardware":
                        for hardware in child_nodes(sub_node):
                            hardware_list.append(self.parse_hardware_mapping(hardware))

        return hardware_list

    @staticmethod
    def parse_hardware_mapping(hardware_node: Document) -> Hardware:
        """Parse hardware mapping."""
        identifier: str = attr(hardware_node.attributes.get("Id"))
        name: str = attr(hardware_node.attributes.get("Name"))
        product_node = hardware_node.getElementsByTagName("Product")[0]
        text: str = attr(product_node.attributes.get("Text"))

        return Hardware(identifier, name, text)

    @staticmethod
    def _get_relevant_files(extraction_path: Path) -> Iterator[Path]:
        """Get all manufactures Hardware.xml in given KNX ZIP file."""
        return extraction_path.glob("**/M-*/Hardware.xml")
