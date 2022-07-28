"""Hardware Loader."""
from xml.dom.minidom import Document, parse
from zipfile import Path

from xknxproject.models import Hardware
from xknxproject.util import attr, child_nodes
from xknxproject.zip import KNXProjContents

from .loader import XMLLoader


class HardwareLoader(XMLLoader):
    """Load hardware from KNX XML."""

    def load(self, project_contents: KNXProjContents) -> list[Hardware]:
        """Load Hardware mappings."""
        hardware_list: list[Hardware] = []
        for xml_file in self._get_relevant_files(project_contents):
            with xml_file.open() as hardware_xml:
                dom: Document = parse(hardware_xml)
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
    def _get_relevant_files(project_contents: KNXProjContents) -> list[Path]:
        """Get all manufactures Hardware.xml in given KNX ZIP file."""
        # M-*/Hardware.xml
        manufacturer_dirs = [
            child
            for child in project_contents.root_path.iterdir()
            if child.is_dir() and child.name.startswith("M-")
        ]
        return [
            xml_file
            for manufacturer in manufacturer_dirs
            if (xml_file := (manufacturer / "Hardware.xml")).exists()
        ]
