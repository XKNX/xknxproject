"""KNX Master Data Loader."""
from __future__ import annotations

from xml.etree import ElementTree
from zipfile import Path


class KNXMasterLoader:
    """Load KNX master XML."""

    @staticmethod
    def load(
        knx_master_file: Path,
        language_code: str | None,
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Load KNX master data."""
        manufacturer_mapping: dict[str, str] = {}
        space_usage_mapping: dict[str, str] = {}

        with knx_master_file.open(mode="rb") as master_xml:
            tree = ElementTree.parse(master_xml)
            for manufacturer in tree.findall(".//{*}Manufacturers/{*}Manufacturer"):
                identifier = manufacturer.get("Id", "")
                manufacturer_mapping[identifier] = manufacturer.get("Name", "")

            for space_usage_node in tree.findall(".//{*}SpaceUsages/{*}SpaceUsage"):
                identifier = space_usage_node.get("Id", "")
                space_usage_mapping[identifier] = space_usage_node.get("Text", "")

            if language_code:
                for translation_element in tree.findall(
                    ".//{*}Languages"
                    f"/{{*}}Language[@Identifier='{language_code}']"
                    "/{*}TranslationUnit/{*}TranslationElement"
                ):
                    _ref_id = translation_element.get("RefId")
                    if _ref_id not in space_usage_mapping:
                        continue
                    if (
                        translation_node := translation_element.find(
                            "{*}Translation[@AttributeName='Text']"
                        )
                    ) is not None:
                        space_usage_mapping[_ref_id] = translation_node.get("Text", "")

        return manufacturer_mapping, space_usage_mapping
