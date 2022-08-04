"""Hardware Loader."""
from zipfile import Path

from lxml import etree

from xknxproject.models import Hardware
from xknxproject.zip import KNXProjContents


class HardwareLoader:
    """Load hardware from KNX XML."""

    def load(self, project_contents: KNXProjContents) -> list[Hardware]:
        """Load Hardware mappings."""
        hardware_list: list[Hardware] = []

        for xml_file in HardwareLoader._get_relevant_files(project_contents):
            with xml_file.open(mode="rb") as hardware_xml:
                for _, elem in etree.iterparse(hardware_xml, tag="{*}Manufacturer"):
                    for hardware in elem.find("{*}Hardware"):
                        hardware_list.append(
                            HardwareLoader.parse_hardware_element(hardware)
                        )
                    elem.clear()

        return hardware_list

    @staticmethod
    def parse_hardware_element(hardware_node: etree.Element) -> Hardware:
        """Parse hardware mapping."""
        identifier: str = hardware_node.get("Id")
        name: str = hardware_node.get("Name")
        _product_node = hardware_node.find(".//{*}Product")
        text: str = _product_node.get("Text") if _product_node is not None else ""

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
