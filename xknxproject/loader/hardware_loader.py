"""Hardware Loader."""

from __future__ import annotations

from xml.etree import ElementTree
from zipfile import Path

from xknxproject.models import HardwareToPrograms, Product
from xknxproject.zip import KNXProjContents


def _flag(node: ElementTree.Element, attr: str) -> bool:
    """Read a knx:Bool_t attribute (default false)."""
    return node.get(attr, "false") == "true"


def _opt_int(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


def _opt_float(value: str | None) -> float | None:
    return float(value) if value not in (None, "") else None


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
        # Hardware-level attributes (identity + capability flags) apply to every product of this
        # hardware, so they are copied onto each Product below.
        hardware_attributes: dict[str, object] = {
            "hardware_name": hardware_name,
            "hardware_serial_number": hardware_node.get("SerialNumber", ""),
            "version_number": _opt_int(hardware_node.get("VersionNumber")),
            "bus_current": _opt_float(hardware_node.get("BusCurrent")),
            "has_individual_address": _flag(hardware_node, "HasIndividualAddress"),
            "has_application_program": _flag(hardware_node, "HasApplicationProgram"),
            "has_application_program2": _flag(hardware_node, "HasApplicationProgram2"),
            "tp256": _flag(hardware_node, "Tp256"),
            "original_manufacturer": hardware_node.get("OriginalManufacturer", ""),
            "no_download_without_plugin": _flag(
                hardware_node, "NoDownloadWithoutPlugin"
            ),
            "is_coupler": _flag(hardware_node, "IsCoupler"),
            "is_power_supply": _flag(hardware_node, "IsPowerSupply"),
            "is_choke": _flag(hardware_node, "IsChoke"),
            "is_power_line_repeater": _flag(hardware_node, "IsPowerLineRepeater"),
            "is_power_line_signal_filter": _flag(
                hardware_node, "IsPowerLineSignalFilter"
            ),
            "is_cable": _flag(hardware_node, "IsCable"),
            "is_ip_enabled": _flag(hardware_node, "IsIPEnabled"),
            "is_rf_retransmitter": _flag(hardware_node, "IsRFRetransmitter"),
            "is_accessory": _flag(hardware_node, "IsAccessory"),
        }
        for product_node in hardware_node.findall("{*}Products/{*}Product"):
            _product = HardwareLoader.parse_product_element(product_node)
            for attr, value in hardware_attributes.items():
                setattr(_product, attr, value)
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
        attributes = {
            name: attribute_node.get("Value", "")
            for attribute_node in product_node.findall("{*}Attributes/{*}Attribute")
            if (name := attribute_node.get("Name"))
        }
        return Product(
            identifier=product_node.get("Id", ""),
            text=product_node.get("Text", ""),
            order_number=product_node.get("OrderNumber", ""),
            is_rail_mounted=_flag(product_node, "IsRailMounted"),
            width_in_millimeter=_opt_float(product_node.get("WidthInMillimeter")),
            visible_description=product_node.get("VisibleDescription", ""),
            default_language=product_node.get("DefaultLanguage", ""),
            hash=product_node.get("Hash", ""),
            non_reg_relevant_data_version=_opt_int(
                product_node.get("NonRegRelevantDataVersion")
            ),
            internal_description=product_node.get("InternalDescription", ""),
            attributes=attributes,
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
