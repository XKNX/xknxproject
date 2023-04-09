"""Application Program Loader."""
from __future__ import annotations

import logging
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

        in_language = False
        in_translation_ref: dict[str, str] | None = None
        translation_map: dict[str, dict[str, str]] = {}

        with application_program_path.open(mode="rb") as application_xml:
            for _, elem in ElementTree.iterparse(application_xml, events=("start",)):
                if elem.tag.endswith("ComObject"):
                    # we take all since we don't know which are referenced to yet
                    identifier = elem.attrib.get("Id")
                    com_objects[identifier] = ComObject(
                        identifier=identifier,
                        name=elem.get("Name"),
                        text=elem.get("Text"),
                        number=int(elem.get("Number", 0)),
                        function_text=elem.get("FunctionText"),
                        object_size=elem.get("ObjectSize"),
                        read_flag=parse_xml_flag(elem.get("ReadFlag"), False),
                        write_flag=parse_xml_flag(elem.get("WriteFlag"), False),
                        communication_flag=parse_xml_flag(
                            elem.get("CommunicationFlag"), False
                        ),
                        transmit_flag=parse_xml_flag(elem.get("TransmitFlag"), False),
                        update_flag=parse_xml_flag(elem.get("UpdateFlag"), False),
                        read_on_init_flag=parse_xml_flag(
                            elem.get("ReadOnInitFlag"), False
                        ),
                        datapoint_type=parse_dpt_types(
                            elem.get("DatapointType", "").split(" ")
                        ),
                    )
                elif elem.tag.endswith("ComObjectRef"):
                    identifier = elem.attrib.get("Id")
                    if identifier not in used_com_object_ref_ids:
                        elem.clear()
                        continue
                    _dpt_type = elem.get("DatapointType")
                    datapoint_type = (
                        parse_dpt_types(_dpt_type.split(" ")) if _dpt_type else None
                    )
                    com_object_refs[identifier] = ComObjectRef(
                        identifier=identifier,
                        ref_id=elem.get("RefId"),
                        name=elem.get("Name"),
                        text=elem.get("Text"),
                        function_text=elem.get("FunctionText"),
                        object_size=elem.get("ObjectSize"),
                        read_flag=parse_xml_flag(elem.get("ReadFlag")),
                        write_flag=parse_xml_flag(elem.get("WriteFlag")),
                        communication_flag=parse_xml_flag(
                            elem.get("CommunicationFlag")
                        ),
                        transmit_flag=parse_xml_flag(elem.get("TransmitFlag")),
                        update_flag=parse_xml_flag(elem.get("UpdateFlag")),
                        read_on_init_flag=parse_xml_flag(elem.get("ReadOnInitFlag")),
                        datapoint_type=datapoint_type,
                    )
                # Translations
                elif elem.tag.endswith("Language"):
                    if in_language or language_code is None:
                        # Already found the language we are looking for or we are not translating
                        # We don't need anything after that tag (there isn't much anyway)
                        elem.clear()
                        break
                    in_language = elem.get("Identifier") == language_code
                elif in_language and elem.tag.endswith("TranslationElement"):
                    in_translation_ref = translation_map[elem.get("RefId")] = {}
                elif (
                    in_language
                    and in_translation_ref is not None
                    and elem.tag.endswith("Translation")
                ):
                    in_translation_ref[elem.get("AttributeName")] = elem.get("Text")
                elem.clear()

            if translation_map:
                ApplicationProgramLoader.apply_translations(
                    com_object_refs, translation_map
                )
                ApplicationProgramLoader.apply_translations(
                    com_objects, translation_map
                )

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
    def apply_translations(
        com_objects: dict[str, ComObject] | dict[str, ComObjectRef],
        translation_map: dict[str, dict[str, str]],
    ) -> None:
        """Apply translations to ComObjects and ComObjectRefs."""
        for com_object in com_objects.values():
            if translation := translation_map.get(com_object.identifier):
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
