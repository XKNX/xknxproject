"""Application Program Loader."""
from __future__ import annotations

from collections.abc import Iterator
import logging
from typing import Any
from xml.etree import ElementTree
from zipfile import Path

from xknxproject.models import ComObject, ComObjectRef, DeviceInstance
from xknxproject.util import parse_dpt_types, parse_xml_flag

_LOGGER = logging.getLogger("xknxproject.log")


class ApplicationProgramLoader:
    """Load the application program from KNX XML."""

    @staticmethod
    def load(
        application_program_path: Path,
        devices: list[DeviceInstance],
        language_code: str | None,
    ) -> None:  # tuple[dict[str, ComObjectRef], dict[str, ComObject]]:
        """Load Hardware mappings and assign to devices."""
        com_object_instance_refs = [
            instance_ref
            for device in devices
            for instance_ref in device.com_object_instance_refs
        ]
        used_com_object_ref_ids = {
            instance_ref.com_object_ref_id
            for instance_ref in com_object_instance_refs
            if instance_ref.com_object_ref_id is not None
        }
        com_object_refs: dict[str, ComObjectRef] = {}  # {Id: ComObjectRef}
        com_objects: dict[str, ComObject] = {}  # {Id: ComObject}

        used_module_arguments = {
            attribute.ref_id: ""
            for device in devices
            for attribute in device.module_instance_arguments()
        }

        with application_program_path.open(mode="rb") as application_xml:
            tree_iterator = ElementTree.iterparse(application_xml, events=("start",))
            for _, elem in tree_iterator:
                if elem.tag.endswith("ComObject"):
                    # we take all since we don't know which are referenced to yet
                    identifier = elem.attrib.get("Id")
                    com_objects[identifier] = ApplicationProgramLoader.parse_com_object(
                        elem, identifier
                    )
                elif elem.tag.endswith("ComObjectRef"):
                    if (_id := elem.attrib.get("Id")) in used_com_object_ref_ids:
                        com_object_refs[
                            _id
                        ] = ApplicationProgramLoader.parse_com_object_ref(elem, _id)
                    elem.clear()
                elif elem.tag.endswith("Argument"):  # ModuleDefs/ModuleDef/Arguments/
                    if (_id := elem.attrib.get("Id")) in used_module_arguments:
                        used_module_arguments[_id] = elem.attrib.get("Name")
                    elem.clear()
                elif elem.tag.endswith("Languages"):
                    elem.clear()
                    # hold iterator for optional translation parsing
                    break
                elem.clear()

            if language_code is not None:
                ApplicationProgramLoader.parse_translations(
                    tree_iterator=tree_iterator,
                    com_objects=com_objects,
                    com_object_refs=com_object_refs,
                    used_com_object_ref_ids=used_com_object_ref_ids,
                    language_code=language_code,
                )

            for device in devices:
                for attribute in device.module_instance_arguments():
                    attribute.name = used_module_arguments[attribute.ref_id]

            for com_instance in com_object_instance_refs:
                if com_instance.com_object_ref_id is None:
                    _LOGGER.warning(
                        "ComObjectInstanceRef %s has no ComObjectRefId",
                        com_instance.identifier,
                    )
                    continue
                _com_object_ref = com_object_refs[com_instance.com_object_ref_id]
                com_instance.merge_from_application(_com_object_ref)
                com_instance.merge_from_application(com_objects[_com_object_ref.ref_id])

    @staticmethod
    def parse_translations(
        tree_iterator: Iterator[tuple[str, Any]],
        com_objects: dict[str, ComObject],
        com_object_refs: dict[str, ComObjectRef],
        used_com_object_ref_ids: set[str],
        language_code: str,
    ) -> None:
        """Parse translations. Replace translated text in com_objects and com_object_refs."""
        used_com_object_ids = {
            com_object_ref.ref_id for com_object_ref in com_object_refs.values()
        }
        used_translation_ids = used_com_object_ids | used_com_object_ref_ids
        in_language = False
        in_translation_ref: str | None = None  # TranslationElement RefId
        # translation_map: {TranslationElement RefId: {AttributeName: Text}}
        translation_map: dict[str, dict[str, str]] = {}
        for _, elem in tree_iterator:
            if elem.tag.endswith("Language"):
                if in_language:
                    # Already found the language we are looking for.
                    # We don't need anything after that tag (there isn't much anyway)
                    elem.clear()
                    break
                in_language = elem.get("Identifier") == language_code
            elif in_language and elem.tag.endswith("TranslationElement"):
                ref_id = elem.get("RefId")
                in_translation_ref = ref_id if ref_id in used_translation_ids else None
            elif (
                in_language
                and in_translation_ref is not None
                and elem.tag.endswith("Translation")
            ):
                translation_map.setdefault(in_translation_ref, {})[
                    elem.get("AttributeName")
                ] = elem.get("Text")
            elem.clear()

        ApplicationProgramLoader.apply_translations(com_object_refs, translation_map)
        ApplicationProgramLoader.apply_translations(com_objects, translation_map)

    @staticmethod
    def parse_com_object(
        elem: ElementTree.Element,
        identifier: str,
    ) -> ComObject:
        """Parse ComObject tag."""
        return ComObject(
            identifier=identifier,
            name=elem.get("Name"),  # type: ignore[arg-type]
            text=elem.get("Text"),  # type: ignore[arg-type]
            number=int(elem.get("Number", 0)),
            function_text=elem.get("FunctionText"),  # type: ignore[arg-type]
            object_size=elem.get("ObjectSize"),  # type: ignore[arg-type]
            read_flag=parse_xml_flag(elem.get("ReadFlag"), False),
            write_flag=parse_xml_flag(elem.get("WriteFlag"), False),
            communication_flag=parse_xml_flag(elem.get("CommunicationFlag"), False),
            transmit_flag=parse_xml_flag(elem.get("TransmitFlag"), False),
            update_flag=parse_xml_flag(elem.get("UpdateFlag"), False),
            read_on_init_flag=parse_xml_flag(elem.get("ReadOnInitFlag"), False),
            datapoint_types=parse_dpt_types(elem.get("DatapointType")),
            base_number_argument_ref=elem.get("BaseNumber"),
        )

    @staticmethod
    def parse_com_object_ref(
        elem: ElementTree.Element,
        identifier: str,
    ) -> ComObjectRef:
        """Parse ComObjectRef tag."""
        return ComObjectRef(
            identifier=identifier,
            ref_id=elem.get("RefId"),  # type: ignore[arg-type]
            name=elem.get("Name"),
            text=elem.get("Text"),
            function_text=elem.get("FunctionText"),
            object_size=elem.get("ObjectSize"),
            read_flag=parse_xml_flag(elem.get("ReadFlag")),
            write_flag=parse_xml_flag(elem.get("WriteFlag")),
            communication_flag=parse_xml_flag(elem.get("CommunicationFlag")),
            transmit_flag=parse_xml_flag(elem.get("TransmitFlag")),
            update_flag=parse_xml_flag(elem.get("UpdateFlag")),
            read_on_init_flag=parse_xml_flag(elem.get("ReadOnInitFlag")),
            datapoint_types=parse_dpt_types(elem.get("DatapointType")),
        )

    @staticmethod
    def apply_translations(
        com_objects: dict[str, ComObject] | dict[str, ComObjectRef],
        translation_map: dict[str, dict[str, str]],
    ) -> None:
        """Apply translations to ComObjects and ComObjectRefs."""
        for identifier in com_objects.keys() & translation_map.keys():
            translation = translation_map[identifier]
            com_object = com_objects[identifier]
            if _text := translation.get("Text"):
                com_object.text = _text
            if _function_text := translation.get("FunctionText"):
                com_object.function_text = _function_text

    @staticmethod
    def get_application_program_files_for_devices(
        project_root_path: Path,
        devices: list[DeviceInstance],
    ) -> dict[Path, list[DeviceInstance]]:
        """Do not load the same application program multiple times."""
        _result: dict[str, list[DeviceInstance]] = {}
        for device in devices:
            if device.application_program_ref:
                # zipfile.Path hashes are not equal, therefore we use str to create the struct
                xml_file_name = device.application_program_xml()
                _result.setdefault(xml_file_name, []).append(device)

        return {
            (project_root_path / xml_file): devices
            for xml_file, devices in _result.items()
        }
