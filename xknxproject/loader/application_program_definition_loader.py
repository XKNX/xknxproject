"""Load the full definition of an application program."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import logging
import re
from typing import IO, Any
from xml.etree import ElementTree
from zipfile import Path

from xknxproject.models import (
    ChannelDefinition,
    DPTType,
    Flags,
    ModuleDefinition,
    ObjectDefinition,
)
from xknxproject.util import (
    parse_dpt_types,
    parse_semantics_dpas,
    parse_semantics_functional_blocks,
    parse_xml_flag,
)

_LOGGER = logging.getLogger("xknxproject.log")

_KIM_VERSION_RE = re.compile(r"KIM-Version=\(<[^>]*>,\s*(\d+),\s*(\d+)\)")


@dataclass
class RawApplicationProgramIdentity:
    """Identity attributes read from the ApplicationProgram root element."""

    application_id: str
    application_number: int | None
    application_version: int | None
    name: str
    mask_version: str
    program_hash: str | None
    kim_version: str | None
    original_manufacturer: str | None  # OEM programs: "M-000A"


@dataclass
class LoadedApplicationProgram:
    """Result of `ApplicationProgramDefinitionLoader.load()`."""

    identity: RawApplicationProgramIdentity
    channels: dict[str, ChannelDefinition]
    modules: dict[str, ModuleDefinition]
    objects: dict[str, ObjectDefinition]
    channel_independent_object_ids: list[str]


@dataclass
class _ComObject:
    """ComObject attributes."""

    name: str
    text: str
    number: int
    function_text: str
    object_size: str
    flags: Flags
    datapoint_types: list[DPTType]


@dataclass
class _ComObjectRef:
    """ComObjectRef attributes - None means "inherit from ComObject"."""

    ref_id: str
    name: str | None
    text: str | None
    function_text: str | None
    object_size: str | None
    read_flag: bool | None
    write_flag: bool | None
    communication_flag: bool | None
    transmit_flag: bool | None
    update_flag: bool | None
    read_on_init_flag: bool | None
    datapoint_types: list[DPTType]
    dpas: list[str] | None


@dataclass(frozen=True)
class _Placement:
    """Place of a <Module> instantiation: a channel, a module definition or top level."""

    channel_id: str | None
    module_id: str | None


def _int_or_none(value: str | None) -> int | None:
    """Parse an optional integer attribute."""
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


class ApplicationProgramDefinitionLoader:
    """Load channels, modules and all objects of an application program."""

    @staticmethod
    def load(
        application_program_path: Path | IO[bytes],
        language_code: str | None,
    ) -> LoadedApplicationProgram:
        """Load the definition. Identifiers are returned relative to the application id."""
        if isinstance(application_program_path, Path):
            with application_program_path.open(mode="rb") as application_xml:
                return ApplicationProgramDefinitionLoader._load(
                    application_xml, language_code
                )
        return ApplicationProgramDefinitionLoader._load(
            application_program_path, language_code
        )

    @staticmethod
    def _load(
        application_xml: IO[bytes],
        language_code: str | None,
    ) -> LoadedApplicationProgram:
        com_objects: dict[str, _ComObject] = {}
        com_object_refs: dict[str, _ComObjectRef] = {}
        channels: dict[str, ChannelDefinition] = {}
        modules: dict[str, ModuleDefinition] = {}
        identity: RawApplicationProgramIdentity | None = None
        prefix = ""  # f"{application_id}_"
        # ancestry while walking <Dynamic>: open channel id and open module def ids.
        open_channel: str | None = None
        module_stack: list[str] = []  # nested for SubModuleDefs
        # A ComObjectRefRef outside any Channel and any ModuleDef is channel
        # independent. One inside a ModuleDef without open Channel belongs to the
        # place where the module is instantiated - resolved after the main pass.
        # Candidates are kept in document order: (module id or None, ref id).
        independent_candidates: list[tuple[str | None, str]] = []
        # ordered sets (dict keys): de-duplicate in linear time, keep document order
        channel_refs: dict[str, dict[str, None]] = {}
        module_refs: dict[str, dict[str, None]] = {}
        # (module def id, parent) of every <Module> instantiation in document order
        module_placements: list[tuple[str, _Placement]] = []
        elem: ElementTree.Element

        tree_iterator = ElementTree.iterparse(application_xml, events=("start", "end"))
        _, elem = next(tree_iterator)
        namespace = elem.tag.split("KNX", maxsplit=1)[0]
        ns_application_program = f"{namespace}ApplicationProgram"
        ns_com_object = f"{namespace}ComObject"
        ns_com_object_ref = f"{namespace}ComObjectRef"
        ns_com_object_ref_ref = f"{namespace}ComObjectRefRef"
        ns_channel = f"{namespace}Channel"
        ns_module_def = f"{namespace}ModuleDef"
        ns_module = f"{namespace}Module"
        ns_languages = f"{namespace}Languages"

        def _rel(identifier: str) -> str:
            return identifier.removeprefix(prefix)

        for event, elem in tree_iterator:
            if event == "start":
                if elem.tag == ns_application_program:
                    application_id = elem.attrib["Id"]
                    prefix = f"{application_id}_"
                    identity = RawApplicationProgramIdentity(
                        application_id=application_id,
                        application_number=_int_or_none(elem.get("ApplicationNumber")),
                        application_version=_int_or_none(
                            elem.get("ApplicationVersion")
                        ),
                        name=elem.get("Name", ""),
                        mask_version=elem.get("MaskVersion", ""),
                        program_hash=elem.get("Hash"),
                        kim_version=ApplicationProgramDefinitionLoader._parse_kim_version(
                            elem.get("Semantics")
                        ),
                        original_manufacturer=elem.get("OriginalManufacturer"),
                    )
                elif elem.tag == ns_com_object:
                    com_objects[_rel(elem.attrib["Id"])] = _ComObject(
                        name=elem.get("Name", ""),
                        text=elem.get("Text", ""),
                        number=int(elem.get("Number", 0)),
                        function_text=elem.get("FunctionText", ""),
                        object_size=elem.get("ObjectSize", ""),
                        flags=Flags(
                            read=parse_xml_flag(elem.get("ReadFlag"), False),
                            write=parse_xml_flag(elem.get("WriteFlag"), False),
                            communication=parse_xml_flag(
                                elem.get("CommunicationFlag"), False
                            ),
                            transmit=parse_xml_flag(elem.get("TransmitFlag"), False),
                            update=parse_xml_flag(elem.get("UpdateFlag"), False),
                            read_on_init=parse_xml_flag(
                                elem.get("ReadOnInitFlag"), False
                            ),
                        ),
                        datapoint_types=parse_dpt_types(elem.get("DatapointType")),
                    )
                elif elem.tag == ns_com_object_ref:
                    com_object_refs[_rel(elem.attrib["Id"])] = _ComObjectRef(
                        ref_id=_rel(elem.attrib["RefId"]),
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
                        datapoint_types=parse_dpt_types(elem.get("DatapointType")),
                        dpas=parse_semantics_dpas(elem.get("Semantics")),
                    )
                elif elem.tag == ns_module_def:
                    module_id = _rel(elem.attrib["Id"])
                    module_stack.append(module_id)
                    modules[module_id] = ModuleDefinition(
                        identifier=module_id,
                        name=elem.get("Name", ""),
                        channel_ids=[],
                    )
                elif elem.tag == ns_channel:
                    open_channel = _rel(elem.attrib["Id"])
                    open_module = module_stack[-1] if module_stack else None
                    channels[open_channel] = ChannelDefinition(
                        identifier=open_channel,
                        name=elem.get("Name", ""),
                        text=elem.get("Text"),
                        number=elem.get("Number", ""),
                        functional_blocks=parse_semantics_functional_blocks(
                            elem.get("Semantics")
                        ),
                        module_definition_id=open_module,
                        object_ids=[],
                    )
                    channel_refs[open_channel] = {}
                    if open_module is not None:
                        modules[open_module]["channel_ids"].append(open_channel)
                elif elem.tag == ns_com_object_ref_ref:
                    ref = _rel(elem.attrib["RefId"])
                    if open_channel is not None:
                        channel_refs[open_channel][ref] = None
                    elif module_stack:
                        refs = module_refs.setdefault(module_stack[-1], {})
                        if ref not in refs:
                            refs[ref] = None
                            independent_candidates.append((module_stack[-1], ref))
                    else:
                        independent_candidates.append((None, ref))
                elif elem.tag == ns_module:
                    module_placements.append(
                        (
                            _rel(elem.attrib["RefId"]),
                            _Placement(
                                channel_id=open_channel,
                                module_id=(
                                    module_stack[-1]
                                    if open_channel is None and module_stack
                                    else None
                                ),
                            ),
                        )
                    )
                elif elem.tag == ns_languages:
                    break
                continue

            # end events: close ancestry and free memory
            if elem.tag == ns_channel:
                open_channel = None
            elif elem.tag == ns_module_def:
                module_stack.pop()
            elem.clear()

        if identity is None:
            raise ValueError("ApplicationProgram root element not found")

        channel_independent = ApplicationProgramDefinitionLoader._place_module_refs(
            channel_refs=channel_refs,
            module_ids=list(modules),
            module_refs=module_refs,
            module_placements=module_placements,
            independent_candidates=independent_candidates,
        )

        if language_code is not None:
            ApplicationProgramDefinitionLoader._apply_translations(
                tree_iterator=tree_iterator,
                namespace=namespace,
                language_code=language_code,
                identity=identity,
                com_objects=com_objects,
                com_object_refs=com_object_refs,
                channels=channels,
            )

        objects = ApplicationProgramDefinitionLoader._merge_objects(
            com_objects, com_object_refs, channel_refs
        )
        # invalid catalog data: a ComObjectRefRef without ComObjectRef or a
        # ComObjectRef without ComObject. Every listed id must be a key of `objects`.
        unresolved = {
            ref for refs in channel_refs.values() for ref in refs if ref not in objects
        }
        unresolved.update(ref for ref in channel_independent if ref not in objects)
        unresolved.update(ref for ref in com_object_refs if ref not in objects)
        if unresolved:
            _LOGGER.warning(
                "Application program %s: ignoring object references without "
                "ComObjectRef or ComObject: %s",
                identity.application_id,
                ", ".join(sorted(unresolved)),
            )
            channel_independent = [
                ref for ref in channel_independent if ref not in unresolved
            ]
        for channel_id, refs in channel_refs.items():
            channels[channel_id]["object_ids"] = [ref for ref in refs if ref in objects]
        return LoadedApplicationProgram(
            identity=identity,
            channels=channels,
            modules=modules,
            objects=objects,
            channel_independent_object_ids=channel_independent,
        )

    @staticmethod
    def _place_module_refs(
        channel_refs: dict[str, dict[str, None]],
        module_ids: list[str],
        module_refs: dict[str, dict[str, None]],
        module_placements: list[tuple[str, _Placement]],
        independent_candidates: list[tuple[str | None, str]],
    ) -> list[str]:
        """
        Add module refs to the channels instantiating their module.

        A module instantiated inside another module inherits every placement of
        that module, recursively. Refs are added in instantiation tree order: the
        refs of a module, then those of its sub-modules. Return the channel
        independent refs: refs outside any module and refs of modules instantiated
        outside any channel or never instantiated.
        """
        channel_modules: dict[str, dict[str, None]] = {}
        child_modules: dict[str, dict[str, None]] = {}
        placed_modules: set[str] = set()
        root_modules: list[str] = []
        for module_id, placement in module_placements:
            placed_modules.add(module_id)
            if placement.channel_id is not None:
                channel_modules.setdefault(placement.channel_id, {})[module_id] = None
            elif placement.module_id is not None:
                child_modules.setdefault(placement.module_id, {})[module_id] = None
            else:
                root_modules.append(module_id)
        root_modules.extend(
            module_id for module_id in module_ids if module_id not in placed_modules
        )

        def _reach(module_id: str, reached: set[str]) -> list[str]:
            """Return a module and its sub-modules not reached yet, in tree order."""
            if module_id in reached:  # also guards cyclic instantiation
                return []
            reached.add(module_id)
            result = [module_id]
            for child_id in child_modules.get(module_id, {}):
                result.extend(_reach(child_id, reached))
            return result

        in_channel: set[str] = set()
        for channel_id, placed_module_ids in channel_modules.items():
            reached: set[str] = set()
            for placed_module_id in placed_module_ids:
                for module_id in _reach(placed_module_id, reached):
                    channel_refs[channel_id].update(
                        dict.fromkeys(module_refs.get(module_id, {}))
                    )
            in_channel |= reached

        independent_modules: set[str] = set()
        for module_id in root_modules:
            _reach(module_id, independent_modules)

        channel_independent: dict[str, None] = {}
        for candidate_module_id, ref in independent_candidates:
            if (
                candidate_module_id is None
                or candidate_module_id in independent_modules
                # only reachable through cyclic instantiation - treat as not placed
                or candidate_module_id not in in_channel
            ):
                channel_independent[ref] = None
        return list(channel_independent)

    @staticmethod
    def _parse_kim_version(semantics: str | None) -> str | None:
        """Parse "92.60" from the KIM header of the root Semantics attribute."""
        if not semantics:
            return None
        if (match := _KIM_VERSION_RE.search(semantics)) is None:
            return None
        return f"{match.group(1)}.{match.group(2)}"

    @staticmethod
    def _apply_translations(
        tree_iterator: Iterator[tuple[str, Any]],
        namespace: str,
        language_code: str,
        identity: RawApplicationProgramIdentity,
        com_objects: dict[str, _ComObject],
        com_object_refs: dict[str, _ComObjectRef],
        channels: dict[str, ChannelDefinition],
    ) -> None:
        """Apply Text and FunctionText translations of the requested language."""
        ns_language = f"{namespace}Language"
        ns_translation_element = f"{namespace}TranslationElement"
        ns_translation = f"{namespace}Translation"
        prefix = f"{identity.application_id}_"
        in_language = False
        ref_id: str | None = None
        elem: ElementTree.Element
        for event, elem in tree_iterator:
            if event == "end":
                if elem.tag == ns_language and in_language:
                    elem.clear()
                    break
                elem.clear()
                continue
            if elem.tag == ns_language:
                in_language = elem.get("Identifier") == language_code
            elif in_language and elem.tag == ns_translation_element:
                ref_id = elem.get("RefId", "").removeprefix(prefix)
            elif in_language and ref_id is not None and elem.tag == ns_translation:
                attribute = elem.get("AttributeName")
                text = elem.get("Text")
                if not text:
                    continue
                if ref_id == identity.application_id:
                    if attribute == "Name":
                        identity.name = text
                elif (com_object := com_objects.get(ref_id)) is not None:
                    if attribute == "Text":
                        com_object.text = text
                    elif attribute == "FunctionText":
                        com_object.function_text = text
                elif (com_object_ref := com_object_refs.get(ref_id)) is not None:
                    if attribute == "Text":
                        com_object_ref.text = text
                    elif attribute == "FunctionText":
                        com_object_ref.function_text = text
                elif (channel := channels.get(ref_id)) is not None:
                    if attribute == "Text":
                        channel["text"] = text

    @staticmethod
    def _merge_objects(
        com_objects: dict[str, _ComObject],
        com_object_refs: dict[str, _ComObjectRef],
        channel_refs: dict[str, dict[str, None]],
    ) -> dict[str, ObjectDefinition]:
        """Merge every ComObjectRef with its ComObject into an ObjectDefinition."""
        channel_ids_by_object: dict[str, list[str]] = {}
        for channel_id, refs in channel_refs.items():
            for object_id in refs:
                channel_ids_by_object.setdefault(object_id, []).append(channel_id)

        objects: dict[str, ObjectDefinition] = {}
        for ref_id, ref in com_object_refs.items():
            com_object = com_objects.get(ref.ref_id)
            if com_object is None:
                continue

            def _flag(ref_value: bool | None, base_value: bool) -> bool:
                return base_value if ref_value is None else ref_value

            objects[ref_id] = ObjectDefinition(
                identifier=ref_id,
                com_object_id=ref.ref_id,
                number=com_object.number,
                name=ref.name if ref.name is not None else com_object.name,
                text=ref.text if ref.text is not None else com_object.text,
                function_text=(
                    ref.function_text
                    if ref.function_text is not None
                    else com_object.function_text
                ),
                object_size=(
                    ref.object_size
                    if ref.object_size is not None
                    else com_object.object_size
                ),
                dpts=ref.datapoint_types or com_object.datapoint_types,
                flags=Flags(
                    read=_flag(ref.read_flag, com_object.flags["read"]),
                    write=_flag(ref.write_flag, com_object.flags["write"]),
                    communication=_flag(
                        ref.communication_flag, com_object.flags["communication"]
                    ),
                    transmit=_flag(ref.transmit_flag, com_object.flags["transmit"]),
                    update=_flag(ref.update_flag, com_object.flags["update"]),
                    read_on_init=_flag(
                        ref.read_on_init_flag, com_object.flags["read_on_init"]
                    ),
                ),
                dpas=ref.dpas,
                channel_ids=channel_ids_by_object.get(ref_id, []),
            )
        return objects
