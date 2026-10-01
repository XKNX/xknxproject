"""Parse the full definitions of the application programs used in a project."""

from __future__ import annotations

import logging
import re

from xknxproject.__version__ import __version__
from xknxproject.loader import ApplicationProgramDefinitionLoader
from xknxproject.models import (
    ApplicationProgramDefinition,
    ApplicationProgramIdentity,
    ApplicationPrograms,
    DeviceInstance,
    Product,
    ProductInfo,
)
from xknxproject.xml.parser import XMLParser
from xknxproject.zip.extractor import KNXProjContents

_LOGGER = logging.getLogger("xknxproject.log")
_OEM_SUFFIX_RE = re.compile(r"-O([0-9A-Fa-f]{4})$")


def _group_devices_by_application(
    devices: list[DeviceInstance],
) -> dict[str, list[DeviceInstance]]:
    """Group devices by application program xml file, skipping unresolved ones."""
    result: dict[str, list[DeviceInstance]] = {}
    for device in devices:
        if device.application_program_ref is None:
            continue
        result.setdefault(device.application_program_xml(), []).append(device)
    return result


def _original_manufacturer_id(
    application_id: str, devices: list[DeviceInstance]
) -> str | None:
    """Original manufacturer from the hardware or the "-Oxxxx" id suffix."""
    for device in devices:
        if device.original_manufacturer:
            return device.original_manufacturer
    if (match := _OEM_SUFFIX_RE.search(application_id)) is not None:
        return f"M-{match.group(1).upper()}"
    return None


def _products(
    devices: list[DeviceInstance], products: dict[str, Product]
) -> list[ProductInfo]:
    """Products of the project using an application program, unique by product id."""
    result: dict[str, ProductInfo] = {}
    for device in devices:
        if device.product_ref in result:
            continue
        product = products.get(device.product_ref)
        if product is None:
            continue
        result[device.product_ref] = ProductInfo(
            product_id=product.identifier,
            hardware_id=product.hardware_id,
            hardware_program_id=device.hardware_program_ref,
            hardware_name=product.hardware_name,
            text=product.text,
            order_number=product.order_number,
        )
    return list(result.values())


class ApplicationProgramParser:
    """Parse application program definitions of a project."""

    def __init__(self, knx_proj_contents: KNXProjContents) -> None:
        """Initialize the parser."""
        self.knx_proj_contents = knx_proj_contents

    def parse(self, language: str | None = None) -> ApplicationPrograms:
        """Parse every application program used by a device of the project."""
        project_parser = XMLParser(self.knx_proj_contents)
        project_parser.load_project(language=language)

        result: ApplicationPrograms = {}
        for xml_file, devices in _group_devices_by_application(
            project_parser.devices
        ).items():
            raw_identity, channels, modules, objects, independent = (
                ApplicationProgramDefinitionLoader.load(
                    application_program_path=self.knx_proj_contents.root_path
                    / xml_file,
                    language_code=project_parser.language_code,
                )
            )
            application_id = raw_identity.application_id
            identity = ApplicationProgramIdentity(
                application_id=application_id,
                manufacturer_id=application_id.split("_", maxsplit=1)[0],
                manufacturer_name=devices[0].manufacturer_name,
                original_manufacturer_id=_original_manufacturer_id(
                    application_id, devices
                ),
                application_number=raw_identity.application_number,
                application_version=raw_identity.application_version,
                name=raw_identity.name,
                mask_version=raw_identity.mask_version,
                program_hash=raw_identity.program_hash,
                kim_version=raw_identity.kim_version,
                products=_products(devices, project_parser.products),
            )
            result[application_id] = ApplicationProgramDefinition(
                identity=identity,
                channels=channels,
                modules=modules,
                objects=objects,
                channel_independent_object_ids=independent,
                language_code=project_parser.language_code,
                xknxproject_version=__version__,
            )
            _LOGGER.debug(
                "Parsed application program %s: %s channels, %s objects",
                application_id,
                len(channels),
                len(objects),
            )
        return result
