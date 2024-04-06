"""Hardware Loader."""

from __future__ import annotations

from xml.etree import ElementTree
from zipfile import Path

from xknxproject.models import HardwareToPrograms, Product
from xknxproject.zip import KNXProjContents


class HardwareLoader:
    """Load hardware from KNX XML."""

    @staticmethod
    def load(
        hardware_file: Path,
        language_code: str | None,
    ) -> tuple[dict[str, Product], HardwareToPrograms]:
        """Load Hardware mappings."""
        product_dict: dict[str, Product] = {}
        hardware_programs: HardwareToPrograms = {}

        with hardware_file.open(mode="rb") as hardware_xml:
            tree = ElementTree.parse(hardware_xml)
            for hardware_node in tree.findall(
                ".//{*}Manufacturer/{*}Hardware/{*}Hardware"
            ):
                _products, _hardware_programs = HardwareLoader.parse_hardware_element(
                    hardware_node
                )
                product_dict |= _products
                hardware_programs |= _hardware_programs

            if language_code:
                for translation_element in tree.findall(
                    ".//{*}Manufacturer/{*}Languages"
                    f"/{{*}}Language[@Identifier='{language_code}']"
                    "/{*}TranslationUnit/{*}TranslationElement"
                ):
                    _ref_id = translation_element.get("RefId")
                    if _ref_id not in product_dict:
                        continue
                    HardwareLoader.apply_product_translation(
                        product_dict[_ref_id], translation_element
                    )

        return product_dict, hardware_programs

    @staticmethod
    def parse_hardware_element(
        hardware_node: ElementTree.Element,
    ) -> tuple[dict[str, Product], HardwareToPrograms]:
        """Parse hardware mapping."""
        product_dict: dict[str, Product] = {}
        hardware_programs: HardwareToPrograms = {}

        hardware_name: str = hardware_node.get("Name", "")
        for product_node in hardware_node.findall("{*}Products/{*}Product"):
            _product = HardwareLoader.parse_product_element(product_node)
            _product.hardware_name = hardware_name
            product_dict[_product.identifier] = _product

        for product_node in hardware_node.findall(
            "{*}Hardware2Programs/{*}Hardware2Program[@Id]/{*}ApplicationProgramRef[@RefId]/.."
        ):
            identifier, application_ref = HardwareLoader.parse_hardware2program_element(
                product_node
            )
            hardware_programs[identifier] = application_ref

        return product_dict, hardware_programs

    @staticmethod
    def parse_product_element(product_node: ElementTree.Element) -> Product:
        """Parse product mapping."""
        return Product(
            identifier=product_node.get("Id", ""),
            text=product_node.get("Text", ""),
            order_number=product_node.get("OrderNumber", ""),
        )

    @staticmethod
    def apply_product_translation(
        product: Product,
        translation_element_node: ElementTree.Element,
    ) -> None:
        """Apply translation to product."""
        if (
            text_node := translation_element_node.find(
                "{*}Translation[@AttributeName='Text']"
            )
        ) is not None:
            product.text = text_node.get("Text", "")

    @staticmethod
    def parse_hardware2program_element(
        hardware_to_program_node: ElementTree.Element,
    ) -> tuple[str, str]:
        """Parse hardware2program mapping."""
        identifier: str = hardware_to_program_node.get("Id", "")
        application_program_node = hardware_to_program_node.find(
            "{*}ApplicationProgramRef"
        )
        application_ref = application_program_node.get("RefId", "")  # type: ignore[union-attr]

        return identifier, application_ref

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
