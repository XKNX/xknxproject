"""
Parse the full definitions of the application programs used in a project.

The project, hardware and device data are loaded with `XMLParser` to find the
application program of each device and the products using it. Each
application program XML is then read once, completely, with
`ApplicationProgramDefinitionLoader`.
"""

from __future__ import annotations

import logging
from xml.etree import ElementTree

from xknxproject.__version__ import __version__
from xknxproject.exceptions import XknxProjectException
from xknxproject.loader import (
    ApplicationProgramDefinitionLoader,
    ApplicationProgramLoader,
)
from xknxproject.models import (
    ApplicationProgramDefinition,
    ApplicationProgramIdentity,
    ApplicationPrograms,
    ApplicationProgramsInfo,
    DeviceInstance,
    Product,
    ProductInfo,
)
from xknxproject.util import application_id_original_manufacturer
from xknxproject.xml.parser import XMLParser
from xknxproject.zip.extractor import KNXProjContents

_LOGGER = logging.getLogger("xknxproject.log")


def _original_manufacturer_id(
    application_id: str,
    program_attribute: str | None,
    devices: list[DeviceInstance],
) -> str | None:
    """
    Return the original manufacturer of an OEM application program, else None.

    Sources in order of precedence: the OriginalManufacturer attribute of the
    ApplicationProgram, the "-Oxxxx" suffix of the application id (same rule as
    `canonical_application_id`), and the OriginalManufacturer attribute of the
    Hardware of a device using the program. The program sources describe the
    program itself, the hardware only the device. Upper case like the suffix.
    """
    candidates = (
        program_attribute,
        application_id_original_manufacturer(application_id),
        *(device.original_manufacturer for device in devices),
    )
    return next((candidate.upper() for candidate in candidates if candidate), None)


def _products(
    devices: list[DeviceInstance], products: dict[str, Product]
) -> list[ProductInfo]:
    """Return the products of the project using an application program, once per product id, in device order."""
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
    """
    Parse the application program definitions of a project.

    Independent of `XMLParser.parse()`: the project data is loaded again and each
    application program used by a device is read completely.
    """

    def __init__(self, knx_proj_contents: KNXProjContents) -> None:
        """Initialize the parser."""
        self.knx_proj_contents = knx_proj_contents

    def parse(self, language: str | None = None) -> ApplicationPrograms:
        """
        Parse every application program used by a device of the project.

        language: language as for `XMLParser.parse()`, e.g. "de-DE"; resolved
            against the languages of the project

        Return the `info` block and the definitions keyed by application program
        id. Devices whose application program can not be resolved are skipped
        (logged while loading the project); an application program that can not
        be read is skipped with a warning.
        """
        project_parser = XMLParser(self.knx_proj_contents)
        # same package: the load step of XMLParser is internal, not public API
        project_parser._load_project(language=language)  # noqa: SLF001  # pylint: disable=protected-access

        program_files = (
            ApplicationProgramLoader.get_application_program_files_for_devices(
                devices=project_parser.devices
            )
        )
        definitions: dict[str, ApplicationProgramDefinition] = {}
        for xml_file, devices in program_files.items():
            # the definitions are independent: one unreadable program (missing
            # file, malformed XML, missing or invalid attribute) must not hide
            # the others
            try:
                loaded = ApplicationProgramDefinitionLoader.load(
                    application_program_path=self.knx_proj_contents.root_path
                    / xml_file,
                    language_code=project_parser.language_code,
                )
            except (
                XknxProjectException,
                ElementTree.ParseError,
                OSError,
                KeyError,
                ValueError,
            ) as err:
                _LOGGER.warning("Skipping application program %s: %r", xml_file, err)
                continue
            raw_identity = loaded.identity
            application_id = raw_identity.application_id
            identity = ApplicationProgramIdentity(
                application_id=application_id,
                # manufacturer part of the id: the selling manufacturer for OEM programs
                manufacturer_id=application_id.split("_", maxsplit=1)[0],
                # all devices of one program XML share its manufacturer folder
                manufacturer_name=devices[0].manufacturer_name,
                original_manufacturer_id=_original_manufacturer_id(
                    application_id, raw_identity.original_manufacturer, devices
                ),
                application_number=raw_identity.application_number,
                application_version=raw_identity.application_version,
                name=raw_identity.name,
                mask_version=raw_identity.mask_version,
                program_hash=raw_identity.program_hash,
                kim_version=raw_identity.kim_version,
                products=_products(devices, project_parser.products),
            )
            definitions[application_id] = ApplicationProgramDefinition(
                identity=identity,
                channels=loaded.channels,
                modules=loaded.modules,
                objects=loaded.objects,
                channel_independent_object_ids=loaded.channel_independent_object_ids,
            )
            _LOGGER.debug(
                "Parsed application program %s: %s channels, %s objects",
                application_id,
                len(loaded.channels),
                len(loaded.objects),
            )
        return ApplicationPrograms(
            info=ApplicationProgramsInfo(
                language_code=project_parser.language_code,
                xknxproject_version=__version__,
            ),
            application_programs=definitions,
        )
