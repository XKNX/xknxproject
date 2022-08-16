"""Hardware Loader."""
from __future__ import annotations

from xml.etree import ElementTree
from zipfile import Path

from xknxproject.models import Hardware
from xknxproject.zip import KNXProjContents


class HardwareLoader:
    """Load hardware from KNX XML."""

    @staticmethod
    def load(hardware_file: Path) -> list[Hardware]:
        """Load Hardware mappings."""
        hardware_list: list[Hardware] = []

        with hardware_file.open(mode="rb") as hardware_xml:
            tree = ElementTree.parse(hardware_xml)
            for hardware in tree.findall(".//{*}Manufacturer/{*}Hardware/{*}Hardware"):
                hardware_list.append(HardwareLoader.parse_hardware_element(hardware))

        return hardware_list

    @staticmethod
    def parse_hardware_element(hardware_node: ElementTree.Element) -> Hardware:
        """Parse hardware mapping."""
        identifier: str = hardware_node.get("Id", "")
        name: str = hardware_node.get("Name", "")
        _product_node = hardware_node.find(".//{*}Product")
        text: str = _product_node.get("Text", "") if _product_node is not None else ""
        application_program_refs: dict[str, str] = {}
        for hardware2program_element in hardware_node.findall(
            ".//{*}Hardware2Programs/{*}Hardware2Program[@Id]/{*}ApplicationProgramRef[@RefId]/.."
        ):
            application_program_refs[
                hardware2program_element.get("Id")  # type: ignore[index]
            ] = hardware2program_element.find(
                "{*}ApplicationProgramRef"
            ).get(  # type: ignore[union-attr]
                "RefId"
            )  # type: ignore[assignment]

        return Hardware(identifier, name, text, application_program_refs)

    @staticmethod
    def get_hardware_files(project_contents: KNXProjContents) -> list[Path]:
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
