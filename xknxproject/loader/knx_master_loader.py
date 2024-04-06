"""KNX Master Data Loader."""

from __future__ import annotations

import logging
from xml.etree import ElementTree
from zipfile import Path

from xknxproject.const import ETS4_PRODUCT_LANGUAGES
from xknxproject.models import KNXMasterData, TranslationsType
from xknxproject.zip import KNXProjContents

_LOGGER = logging.getLogger("xknxproject.log")


class KNXMasterLoader:
    """Load KNX master XML."""

    @staticmethod
    def load(
        knx_proj_contents: KNXProjContents,
        knx_master_file: Path,
        language: str | None,
    ) -> tuple[KNXMasterData, str | None]:
        """Load KNX master data. Returns KNXMasterData and the found language code."""
        manufacturer_mapping: dict[str, str] = {}
        space_usage_mapping: dict[str, str] = {}
        product_languages: list[str] = []  # eg. "en-US", "de-DE", "fr-FR"
        language_code: str | None = None
        translations: TranslationsType = {}
        function_type_mapping: dict[str, str] = {}

        with knx_master_file.open(mode="rb") as master_xml:
            tree = ElementTree.parse(master_xml)
            for manufacturer in tree.findall(".//{*}Manufacturers/{*}Manufacturer"):
                identifier = manufacturer.get("Id", "")
                manufacturer_mapping[identifier] = manufacturer.get("Name", "")

            if knx_proj_contents.is_ets4_project():
                # No SpaceUsage in ETS4, neither ProductLanguages. Therefore, we use an
                # hardcoded list of common product languages
                product_languages = ETS4_PRODUCT_LANGUAGES
            else:
                for space_usage_node in tree.findall(".//{*}SpaceUsages/{*}SpaceUsage"):
                    identifier = space_usage_node.get("Id", "")
                    space_usage_mapping[identifier] = space_usage_node.get("Text", "")

                for language_node in tree.findall(".//{*}ProductLanguages/{*}Language"):
                    product_languages.append(language_node.get("Identifier", ""))

                for function_type_node in tree.findall(
                    ".//{*}FunctionTypes/{*}FunctionType"
                ):
                    identifier = function_type_node.get("Id", "")
                    function_type_mapping[identifier] = function_type_node.get(
                        "Text", ""
                    )

            if language is not None:
                language_code = KNXMasterLoader.get_language_code(
                    language, product_languages
                )

            if language_code:
                for translation_element in tree.findall(
                    ".//{*}Languages"
                    f"/{{*}}Language[@Identifier='{language_code}']"
                    "/{*}TranslationUnit/{*}TranslationElement"
                ):
                    _ref_id = translation_element.get("RefId", "")
                    translations[_ref_id] = {
                        attr: text
                        for item in translation_element.findall("{*}Translation")
                        if (attr := item.get("AttributeName")) is not None
                        and (text := item.get("Text")) is not None
                    }

        return (
            KNXMasterData(
                function_type_names=function_type_mapping,
                manufacturer_names=manufacturer_mapping,
                space_usage_mapping=space_usage_mapping,
                translations=translations,
            ),
            language_code,
        )

    @staticmethod
    def get_language_code(language: str, product_languages: list[str]) -> str | None:
        """Infer language code from product languages."""
        if language in product_languages:
            return language

        for language_code, country_code in [
            _lan.split("-", maxsplit=1) for _lan in product_languages
        ]:
            if language[:2].lower() == language_code:
                used_language = f"{language_code}-{country_code}"
                _LOGGER.info(
                    'Using language code "%s" for "%s"', used_language, language
                )
                return used_language

        _LOGGER.warning("No matching language code found for %s", language)
        return None
