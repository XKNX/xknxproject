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
    ApplicationProgramSegment,
    ComObject,
    ComObjectRef,
    DeviceInstance,
    ModuleDefinitionArgumentInfo,
    ModuleDefinitionNumericArg,
    Parameter,
    ParameterMemory,
    ParameterRef,
    ParameterType,
)
from xknxproject.util import (
    parse_dpt_types,
    parse_number,
    parse_semantics_dpas,
    parse_semantics_functional_blocks,
    parse_xml_flag,
)

# TypeFloat carries no SizeInBit attribute; the size follows from its encoding
_FLOAT_ENCODING_SIZES = {
    "DPT 9": 16,
    "DPT 14": 32,
    "IEEE-754 Single": 32,
    "IEEE-754 Double": 64,
}


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
                _id: str
                if elem.tag == ns_com_object:
                    # we take all since we don't know which are referenced to yet
                    _id = elem.attrib.get("Id")  # type: ignore[assignment]
                    com_objects[_id] = ApplicationProgramLoader.parse_com_object(
                        elem, _id
                    )
                elif elem.tag == ns_com_object_ref:
                    if (_id := elem.attrib.get("Id")) in used_com_object_ref_ids:  # type: ignore[operator,assignment]
                        com_object_refs[_id] = (
                            ApplicationProgramLoader.parse_com_object_ref(elem, _id)
                        )
                    elem.clear()
                elif elem.tag == ns_allocator:  # Allocators/Allocator
                    _id = elem.attrib.get("Id")  # type: ignore[assignment]
                    allocators[_id] = Allocator(
                        identifier=_id,
                        name=elem.attrib.get("Name"),  # type: ignore[arg-type]
                        start=int(elem.attrib.get("Start")),  # type: ignore[arg-type]
                        end=int(elem.attrib.get("maxInclusive")),  # type: ignore[arg-type]
                    )
                elif elem.tag == ns_argument:
                    # ModuleDefs/ModuleDef/Arguments/
                    # or ModuleDefs/ModuleDef/SubModuleDefs/ModuleDef/Arguments/
                    if (_id := elem.attrib.get("Id")) in used_module_arguments:  # type: ignore[operator,assignment]
                        allocates = elem.attrib.get("Allocates")
                        used_module_arguments[_id] = ModuleDefinitionArgumentInfo(
                            name=elem.attrib.get("Name"),  # type: ignore[arg-type]
                            allocates=int(allocates) if allocates is not None else None,
                        )
                    elem.clear()
                elif elem.tag == ns_numeric_arg:
                    # in dynamic section of Modules
                    if (_id := elem.attrib.get("RefId")) in used_module_arguments:  # type: ignore[operator,assignment]
                        value = elem.attrib.get("Value")
                        numeric_args[_id] = ModuleDefinitionNumericArg(
                            allocator_ref_id=elem.attrib.get("AllocatorRefId"),
                            base_value=elem.attrib.get("BaseValue"),
                            value=int(value) if value is not None else None,
                        )
                    elem.clear()
                elif elem.tag == ns_channel:
                    _id = elem.attrib.get("Id")  # type: ignore[assignment]
                    channels[_id] = ApplicationProgramChannel(
                        identifier=_id,
                        name=elem.attrib.get("Name"),  # type: ignore[arg-type]
                        number=elem.attrib.get("Number"),  # type: ignore[arg-type]
                        text=elem.attrib.get("Text"),
                        text_parameter_ref_id=elem.attrib.get("TextParameterRefId"),
                        semantics=parse_semantics_functional_blocks(
                            elem.attrib.get("Semantics")
                        ),
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
            semantics=parse_semantics_dpas(elem.get("Semantics")),
        )

    @staticmethod
    def load_static(application_program_path: Path) -> ApplicationProgram:
        """
        Load the complete static definition of an application program.

        Unlike :meth:`load`, this is not filtered by device instances (a
        standalone product has none) and additionally parses parameters,
        parameter types and the memory/segment layout - the parts a product
        (``.knxprod``) needs but a project (``.knxproj``) does not.
        ModuleDefs (instantiation templates) are not included.
        """
        com_objects: dict[str, ComObject] = {}
        com_object_refs: dict[str, ComObjectRef] = {}
        parameters: dict[str, Parameter] = {}
        parameter_types: dict[str, ParameterType] = {}
        parameter_refs: dict[str, ParameterRef] = {}
        segments: dict[str, ApplicationProgramSegment] = {}
        app_attrs: dict[str, str] = {}

        with application_program_path.open(mode="rb") as application_xml:
            tree_iterator = ElementTree.iterparse(
                application_xml, events=("start", "end")
            )
            _, root = next(tree_iterator)
            namespace = root.tag.split("KNX", maxsplit=1)[0]

            ns_app = f"{namespace}ApplicationProgram"
            ns_dynamic = f"{namespace}Dynamic"
            ns_module_defs = f"{namespace}ModuleDefs"
            ns_com_object = f"{namespace}ComObject"
            ns_com_object_ref = f"{namespace}ComObjectRef"
            ns_parameter = f"{namespace}Parameter"
            ns_parameter_type = f"{namespace}ParameterType"
            ns_parameter_ref = f"{namespace}ParameterRef"
            ns_rel_segment = f"{namespace}RelativeSegment"
            ns_abs_segment = f"{namespace}AbsoluteSegment"
            ns_memory = f"{namespace}Memory"
            ns_union = f"{namespace}Union"

            in_union = False
            for event, elem in tree_iterator:
                if event == "start":
                    # identity is only reliably available on the opening tag
                    if elem.tag == ns_app and not app_attrs:
                        app_attrs = dict(elem.attrib)
                    elif elem.tag == ns_union:
                        in_union = True
                    elif elem.tag in (ns_module_defs, ns_dynamic):
                        # ModuleDefs hold instantiation templates (each with its
                        # own Dynamic section) and the Dynamic section is
                        # UI/visibility logic; neither is part of the static
                        # definition. ModuleDefs precede the Dynamic section.
                        break
                    continue
                # event == "end": element and its children are complete
                _id = elem.get("Id")
                if elem.tag == ns_com_object and _id:
                    com_objects[_id] = ApplicationProgramLoader.parse_com_object(
                        elem, _id
                    )
                elif elem.tag == ns_com_object_ref and _id:
                    com_object_refs[_id] = (
                        ApplicationProgramLoader.parse_com_object_ref(elem, _id)
                    )
                elif elem.tag == ns_parameter and _id:
                    if in_union:
                        # parsed by the enclosing Union end tag
                        continue
                    parameters[_id] = ApplicationProgramLoader.parse_parameter(
                        elem, _id, ns_memory
                    )
                elif elem.tag == ns_union:
                    in_union = False
                    for parameter in ApplicationProgramLoader.parse_union(
                        elem, ns_memory, ns_parameter
                    ):
                        parameters[parameter.identifier] = parameter
                elif elem.tag == ns_parameter_type and _id:
                    parameter_types[_id] = (
                        ApplicationProgramLoader.parse_parameter_type(
                            elem, _id, namespace
                        )
                    )
                elif elem.tag == ns_parameter_ref and _id:
                    parameter_refs[_id] = ParameterRef(
                        identifier=_id,
                        ref_id=elem.get("RefId"),  # type: ignore[arg-type]
                        value=elem.get("Value"),
                        text=elem.get("Text"),
                    )
                elif elem.tag in (ns_rel_segment, ns_abs_segment) and _id:
                    segments[_id] = ApplicationProgramLoader.parse_segment(
                        elem, _id, relative=elem.tag == ns_rel_segment
                    )
                else:
                    continue
                elem.clear()

        _pei = app_attrs.get("PeiType")
        return ApplicationProgram(
            com_objects=com_objects,
            com_object_refs=com_object_refs,
            allocators={},
            module_def_arguments={},
            numeric_args={},
            channels={},
            identifier=app_attrs.get("Id", ""),
            name=app_attrs.get("Name", ""),
            application_number=int(app_attrs.get("ApplicationNumber", 0)),
            application_version=int(app_attrs.get("ApplicationVersion", 0)),
            mask_version=app_attrs.get("MaskVersion", ""),
            pei_type=int(_pei) if _pei is not None else None,
            load_procedure_style=app_attrs.get("LoadProcedureStyle"),
            dynamic_table_management=app_attrs.get("DynamicTableManagement") == "true",
            parameters=parameters,
            parameter_types=parameter_types,
            parameter_refs=parameter_refs,
            segments=segments,
        )

    @staticmethod
    def parse_parameter(
        elem: ElementTree.Element,
        identifier: str,
        ns_memory: str,
        union_memory: ParameterMemory | None = None,
    ) -> Parameter:
        """Parse a Parameter tag (with optional Memory child)."""
        memory: ParameterMemory | None = None
        mem = elem.find(ns_memory)
        if mem is not None:
            memory = ApplicationProgramLoader.parse_memory(mem)
        elif union_memory is not None:
            # union member: the shared union Memory shifted by the
            # Offset/BitOffset attributes of the Parameter tag itself
            memory = ParameterMemory(
                segment_ref=union_memory.segment_ref,
                offset=union_memory.offset + int(elem.get("Offset", 0)),
                bit_offset=union_memory.bit_offset + int(elem.get("BitOffset", 0)),
                base_offset_ref=union_memory.base_offset_ref,
            )
        return Parameter(
            identifier=identifier,
            name=elem.get("Name"),
            text=elem.get("Text"),
            parameter_type_ref=elem.get("ParameterType"),  # type: ignore[arg-type]
            value=elem.get("Value"),
            memory=memory,
        )

    @staticmethod
    def parse_memory(elem: ElementTree.Element) -> ParameterMemory:
        """Parse a Memory tag."""
        return ParameterMemory(
            segment_ref=elem.get("CodeSegment"),  # type: ignore[arg-type]
            offset=int(elem.get("Offset", 0)),
            bit_offset=int(elem.get("BitOffset", 0)),
            base_offset_ref=elem.get("BaseOffset"),
        )

    @staticmethod
    def parse_union(
        elem: ElementTree.Element, ns_memory: str, ns_parameter: str
    ) -> list[Parameter]:
        """
        Parse a Union tag into its member Parameters.

        Union members share one memory block: the union holds the Memory child
        and each Parameter tag carries its own relative Offset/BitOffset
        attributes instead of an individual Memory child.
        """
        mem = elem.find(ns_memory)
        union_memory = (
            ApplicationProgramLoader.parse_memory(mem) if mem is not None else None
        )
        return [
            ApplicationProgramLoader.parse_parameter(
                parameter, _id, ns_memory, union_memory
            )
            for parameter in elem.findall(ns_parameter)
            if (_id := parameter.get("Id"))
        ]

    @staticmethod
    def parse_parameter_type(
        elem: ElementTree.Element, identifier: str, namespace: str
    ) -> ParameterType:
        """Parse a ParameterType tag and its restriction child."""
        kind = ""
        size_in_bit: int | None = None
        base: str | None = None
        minimum: int | float | None = None
        maximum: int | float | None = None
        encoding: str | None = None
        enumerations: dict[int, str] = {}

        for child in elem:  # the single restriction child (TypeNumber/TypeText/...)
            kind = child.tag.removeprefix(namespace)
            _size = child.get("SizeInBit")
            size_in_bit = int(_size) if _size is not None else None
            base = child.get("Base")
            minimum = parse_number(child.get("minInclusive"))
            maximum = parse_number(child.get("maxInclusive"))
            encoding = child.get("Encoding")
            if size_in_bit is None and encoding is not None:
                size_in_bit = _FLOAT_ENCODING_SIZES.get(encoding)
            for enum in child.findall(f"{namespace}Enumeration"):
                enumerations[int(enum.get("Value", 0))] = enum.get("Text", "")
            break

        return ParameterType(
            identifier=identifier,
            name=elem.get("Name", ""),
            kind=kind,
            size_in_bit=size_in_bit,
            base=base,
            minimum=minimum,
            maximum=maximum,
            encoding=encoding,
            enumerations=enumerations,
        )

    @staticmethod
    def parse_segment(
        elem: ElementTree.Element, identifier: str, relative: bool
    ) -> ApplicationProgramSegment:
        """Parse a RelativeSegment / AbsoluteSegment tag."""
        _size = elem.get("Size")
        _lsm = elem.get("LoadStateMachine")
        _offset = elem.get("Offset")
        _address = elem.get("Address")
        return ApplicationProgramSegment(
            identifier=identifier,
            kind="relative" if relative else "absolute",
            size=int(_size) if _size is not None else None,
            load_state_machine=int(_lsm) if _lsm is not None else None,
            offset=int(_offset) if _offset is not None else None,
            address=int(_address) if _address is not None else None,
            memory_type=elem.get("MemoryType"),
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
