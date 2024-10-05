"""Application Program Loader."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from xml.etree import ElementTree
from zipfile import Path

from xknxproject.models import (
    Allocator,
    ApplicationProgram,
    ApplicationProgramChannel,
    ComObject,
    ComObjectRef,
    DeviceInstance,
    ModuleDefinitionArgumentInfo,
    ModuleDefinitionNumericArg,
)
from xknxproject.util import parse_dpt_types, parse_xml_flag


class ApplicationProgramLoader:
    """Load the application program from KNX XML."""

    @staticmethod
    def load(
        application_program_path: Path,
        devices: list[DeviceInstance],
        language_code: str | None,
    ) -> ApplicationProgram:
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

        used_module_arguments: dict[str, ModuleDefinitionArgumentInfo] = {
            attribute.ref_id: ModuleDefinitionArgumentInfo()
            for device in devices
            for attribute in device.module_instance_arguments()
        }
        numeric_args: dict[str, ModuleDefinitionNumericArg] = {}
        channels: dict[
            str, ApplicationProgramChannel
        ] = {}  # {Id: ApplicationProgramChannel}
        allocators: dict[str, Allocator] = {}

        with application_program_path.open(mode="rb") as application_xml:
            tree_iterator = ElementTree.iterparse(application_xml, events=("start",))
            # get namespace from root element
            _, elem = next(tree_iterator)
            namespace = elem.tag.split("KNX", maxsplit=1)[0]
            # define namespaced tag strings for faster comparison - ~15% faster
            # than elem.tag.endswith("tagname") or elem.tag == f"{namespace}tagname"
            ns_com_object = f"{namespace}ComObject"
            ns_com_object_ref = f"{namespace}ComObjectRef"
            ns_allocator = f"{namespace}Allocator"
            ns_argument = f"{namespace}Argument"
            ns_numeric_arg = f"{namespace}NumericArg"
            ns_channel = f"{namespace}Channel"
            ns_languages = f"{namespace}Languages"

            for _, elem in tree_iterator:
                if elem.tag == ns_com_object:
                    # we take all since we don't know which are referenced to yet
                    identifier = elem.attrib.get("Id")
                    com_objects[identifier] = ApplicationProgramLoader.parse_com_object(
                        elem, identifier
                    )
                elif elem.tag == ns_com_object_ref:
                    if (_id := elem.attrib.get("Id")) in used_com_object_ref_ids:
                        com_object_refs[_id] = (
                            ApplicationProgramLoader.parse_com_object_ref(elem, _id)
                        )
                    elem.clear()
                elif elem.tag == ns_allocator:  # Allocators/Allocator
                    allocators[elem.attrib.get("Id")] = Allocator(
                        identifier=elem.attrib.get("Id"),
                        name=elem.attrib.get("Name"),
                        start=int(elem.attrib.get("Start")),
                        end=int(elem.attrib.get("maxInclusive")),
                    )
                elif elem.tag == ns_argument:
                    # ModuleDefs/ModuleDef/Arguments/
                    # or ModuleDefs/ModuleDef/SubModuleDefs/ModuleDef/Arguments/
                    if (_id := elem.attrib.get("Id")) in used_module_arguments:
                        allocates = elem.attrib.get("Allocates")
                        used_module_arguments[_id] = ModuleDefinitionArgumentInfo(
                            name=elem.attrib.get("Name"),
                            allocates=int(allocates) if allocates is not None else None,
                        )
                    elem.clear()
                elif elem.tag == ns_numeric_arg:
                    # in dynamic section of Modules
                    if (_id := elem.attrib.get("RefId")) in used_module_arguments:
                        value = elem.attrib.get("Value")
                        numeric_args[_id] = ModuleDefinitionNumericArg(
                            allocator_ref_id=elem.attrib.get("AllocatorRefId"),
                            base_value=elem.attrib.get("BaseValue"),
                            value=int(value) if value is not None else None,
                        )
                    elem.clear()
                elif elem.tag == ns_channel:
                    _id = elem.attrib.get("Id")
                    channels[_id] = ApplicationProgramChannel(
                        identifier=_id,
                        name=elem.attrib.get("Name"),
                        number=elem.attrib.get("Number"),
                        text=elem.attrib.get("Text"),
                        text_parameter_ref_id=elem.attrib.get("TextParameterRefId"),
                    )
                    elem.clear()
                elif elem.tag == ns_languages:
                    elem.clear()
                    # hold iterator for optional translation parsing
                    break
                elem.clear()

            if language_code is not None:
                ApplicationProgramLoader.parse_translations(
                    tree_iterator=tree_iterator,
                    namespace=namespace,
                    com_objects=com_objects,
                    com_object_refs=com_object_refs,
                    used_com_object_ref_ids=used_com_object_ref_ids,
                    channels=channels,
                    language_code=language_code,
                )

            return ApplicationProgram(
                com_objects=com_objects,
                com_object_refs=com_object_refs,
                allocators=allocators,
                module_def_arguments=used_module_arguments,
                numeric_args=numeric_args,
                channels=channels,
            )

    @staticmethod
    def parse_translations(
        tree_iterator: Iterator[tuple[str, Any]],
        namespace: str,
        com_objects: dict[str, ComObject],
        com_object_refs: dict[str, ComObjectRef],
        used_com_object_ref_ids: set[str],
        channels: dict[str, ApplicationProgramChannel],
        language_code: str,
    ) -> None:
        """Parse translations. Replace translated text in com_objects and com_object_refs."""
        _used_com_object_ids = {
            com_object_ref.ref_id for com_object_ref in com_object_refs.values()
        }
        used_translation_ids = (
            _used_com_object_ids | used_com_object_ref_ids | channels.keys()
        )
        in_language = False
        in_translation_ref: str | None = None  # TranslationElement RefId
        # translation_map: {TranslationElement RefId: {AttributeName: Text}}
        translation_map: dict[str, dict[str, str]] = {}

        ns_language = f"{namespace}Language"
        ns_translation_element = f"{namespace}TranslationElement"
        ns_translation = f"{namespace}Translation"

        for _, elem in tree_iterator:
            if elem.tag == ns_language:
                if in_language:
                    # Hitting the next language tag after the one we were looking for.
                    # We don't need anything after that tag (there isn't much anyway)
                    elem.clear()
                    break
                in_language = elem.get("Identifier") == language_code
            elif in_language and elem.tag == ns_translation_element:
                ref_id = elem.get("RefId")
                in_translation_ref = ref_id if ref_id in used_translation_ids else None
            elif (
                in_language
                and in_translation_ref is not None
                and elem.tag == ns_translation
            ):
                translation_map.setdefault(in_translation_ref, {})[
                    elem.get("AttributeName")
                ] = elem.get("Text")
            elem.clear()

        ApplicationProgramLoader.apply_translations(com_object_refs, translation_map)
        ApplicationProgramLoader.apply_translations(com_objects, translation_map)
        ApplicationProgramLoader.apply_translations(channels, translation_map)

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
            text_parameter_ref_id=elem.get("TextParameterRefId"),
        )

    @staticmethod
    def apply_translations(
        translatable_object_map: dict[str, ComObject]
        | dict[str, ComObjectRef]
        | dict[str, ApplicationProgramChannel],
        translation_map: dict[str, dict[str, str]],
    ) -> None:
        """Apply translations to Objects."""
        for identifier in translatable_object_map.keys() & translation_map.keys():
            translation = translation_map[identifier]
            obj = translatable_object_map[identifier]
            if _text := translation.get("Text"):
                obj.text = _text
            if hasattr(obj, "function_text") and (
                _function_text := translation.get("FunctionText")
            ):
                obj.function_text = _function_text

    @staticmethod
    def get_application_program_files_for_devices(
        devices: list[DeviceInstance],
    ) -> dict[str, list[DeviceInstance]]:
        """Do not load the same application program multiple times."""
        result: dict[str, list[DeviceInstance]] = {}
        for device in devices:
            if device.application_program_ref:
                # zipfile.Path hashes are not equal, therefore we use str to create the struct
                xml_file_name = device.application_program_xml()
                result.setdefault(xml_file_name, []).append(device)
        return result
