"""
Load the complete definition of one application program XML.

Unlike `ApplicationProgramLoader`, which reads only the parts of an application
program that devices of the project use, this loader reads every ComObject,
ComObjectRef, Channel and ModuleDef of the program in one `iterparse` pass.

Identifiers are returned relative to the application program id
("M-0083_A-013A-32-DCC1_MD-2_CH-1" -> "MD-2_CH-1"). Definitions are not
instantiated, so module definition parts ("MD-2", "MD-4_SM-1") stay and module
instance parts ("_M-1_MI-1") never occur.

Channel membership is structural, independent of parameter values:

* a ComObjectRefRef inside a Channel belongs to that Channel, in every
  `choose`/`when` branch;
* a ComObjectRefRef inside a ModuleDef but outside a Channel of that ModuleDef
  belongs to every Channel in which the module is instantiated by a `<Module>`
  element, directly or through the modules instantiating it (also inside
  `<Repeat>`);
* every other ComObjectRefRef is channel independent: those outside any
  ModuleDef and Channel (ChannelIndependentBlock or top level) and those of
  modules instantiated outside any Channel or never instantiated.

A module instantiated both inside and outside Channels contributes its refs to
both. A ChannelIndependentBlock inside a ModuleDef is not treated specially;
its refs follow the placement of the module (no known catalog has refs there).

Every id listed in a Channel or as channel independent is a key of the
objects: refs without ComObjectRef or ComObject are dropped with a warning.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import logging
import re
from typing import IO, Any
from xml.etree import ElementTree
from zipfile import Path

from xknxproject.exceptions import UnexpectedDataError
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

# KIM header in the root Semantics attribute:
# "... KIM-Version=(<ontology uri>, 92, 60), ..." -> "92.60"
_KIM_VERSION_RE = re.compile(r"KIM-Version=\(<[^>]*>,\s*(\d+),\s*(\d+)\)")


@dataclass
class RawApplicationProgramIdentity:
    """
    Identity attributes of the ApplicationProgram element.

    Only what the application program XML provides; `ApplicationProgramParser`
    adds the manufacturer and the products of the project.
    """

    application_id: str  # "Id" - "M-0083_A-013A-32-DCC1"
    application_number: int | None  # "ApplicationNumber" - None if missing or invalid
    application_version: int | None  # "ApplicationVersion" - None if missing or invalid
    name: str  # "Name" - translated to the requested language
    mask_version: str  # "MaskVersion" - "MV-07B0"
    program_hash: str | None  # "Hash" - base64
    kim_version: str | None  # "92.60" from the KIM header of "Semantics", else None
    original_manufacturer: str | None  # "OriginalManufacturer" - OEM programs: "M-000A"


@dataclass
class LoadedApplicationProgram:
    """
    Result of `ApplicationProgramDefinitionLoader.load()`.

    Dictionaries are keyed by identifier relative to the application program id.
    """

    identity: RawApplicationProgramIdentity
    channels: dict[str, ChannelDefinition]
    modules: dict[str, ModuleDefinition]
    objects: dict[str, ObjectDefinition]
    channel_independent_object_ids: list[str]  # document order


@dataclass
class _ComObject:
    """ComObject of a ComObjectTable, the base of one or more ComObjectRefs."""

    name: str  # "Name"
    text: str  # "Text" - translated
    number: int  # "Number" - inside a ModuleDef relative to the module base number
    function_text: str  # "FunctionText" - translated
    object_size: str  # "ObjectSize" - "1 Bit"
    flags: Flags  # missing flag attributes are False, as in ApplicationProgramLoader
    datapoint_types: list[DPTType]  # "DatapointType" - knx:IDREFS


@dataclass
class _ComObjectRef:
    """
    ComObjectRef overriding attributes of the ComObject it references.

    None, or an empty list of datapoint types, means the attribute is not set on
    the ref and is inherited from the ComObject.
    """

    ref_id: str  # "RefId" - ComObject id relative to the application program
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
    dpas: list[str] | None  # from "Semantics" - DPAs are read from refs only


@dataclass(frozen=True)
class _Placement:
    """
    Parent of one `<Module>` instantiation.

    channel_id is set when the Module element is inside a Channel. Otherwise
    module_id is the ModuleDef whose Dynamic section contains the Module element;
    both are None for a Module outside any Channel and ModuleDef (top level or in
    a ChannelIndependentBlock).
    """

    channel_id: str | None
    module_id: str | None


def _inherit(ref_value: bool | None, base_value: bool) -> bool:
    """Return the flag of the ComObjectRef if set, else the flag of the ComObject."""
    return base_value if ref_value is None else ref_value


def _int_or_none(value: str | None) -> int | None:
    """Parse an optional integer attribute; return None if it is missing or invalid."""
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


class ApplicationProgramDefinitionLoader:
    """
    Load channels, modules and all objects of one application program.

    See the module docstring for identifiers and channel membership.
    """

    @staticmethod
    def load(
        application_program_path: Path | IO[bytes],
        language_code: str | None,
    ) -> LoadedApplicationProgram:
        """
        Load the definition of an application program XML.

        application_program_path: application program XML in the extracted project
            archive, or an open binary stream
        language_code: language of translated texts, e.g. "de-DE"; None keeps the
            texts of the program's default language

        Return the identity, the channel, module and object definitions and the
        channel independent object identifiers. Raise UnexpectedDataError if the
        XML has no ApplicationProgram element.
        """
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
        """
        Walk the XML once with start and end events and build the definition.

        Start events read attributes; end events close the Channel and ModuleDef
        ancestry and clear elements to bound memory. The walk stops at
        <Languages>; `_apply_translations` continues the same iterator.
        """
        com_objects: dict[str, _ComObject] = {}
        com_object_refs: dict[str, _ComObjectRef] = {}
        channels: dict[str, ChannelDefinition] = {}
        modules: dict[str, ModuleDefinition] = {}
        identity: RawApplicationProgramIdentity | None = None
        # "<application id>_": XML ids are absolute, output ids relative; set at
        # the ApplicationProgram start
        prefix = ""
        # ancestry of the current element: the open Channel and the open ModuleDefs
        # (innermost last; SubModuleDefs nest inside their ModuleDef)
        open_channel: str | None = None
        module_stack: list[str] = []
        # refs outside any Channel, in document order, with the ModuleDef containing
        # them (None outside ModuleDefs); which of them are channel independent is
        # known only after all <Module> placements are read, see _place_module_refs
        independent_candidates: list[tuple[str | None, str]] = []
        # ordered sets (dict keys): de-duplicate in linear time, keep document order
        channel_refs: dict[str, dict[str, None]] = {}
        module_refs: dict[str, dict[str, None]] = {}
        # (module def id, parent) of every <Module> instantiation in document order
        module_placements: list[tuple[str, _Placement]] = []
        elem: ElementTree.Element

        tree_iterator = ElementTree.iterparse(application_xml, events=("start", "end"))
        _, elem = next(tree_iterator)
        # the namespace differs per schema version (project/11 ETS 4 ... project/23 ETS 6)
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
            """Return an id relative to the application program ("<application id>_" removed)."""
            return identifier.removeprefix(prefix)

        # start events: attributes are complete; end events: close ancestry and clear
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
                        # inside a ModuleDef but outside its Channels: the channels are
                        # known only after all <Module> placements are read.
                        # De-duplicated per module here; candidates outside modules
                        # are de-duplicated in _place_module_refs
                        refs = module_refs.setdefault(module_stack[-1], {})
                        if ref not in refs:
                            refs[ref] = None
                            independent_candidates.append((module_stack[-1], ref))
                    else:
                        independent_candidates.append((None, ref))
                elif elem.tag == ns_module:
                    # inside a Channel the Channel is the parent; otherwise the
                    # enclosing ModuleDef, whose placements are inherited later.
                    # <Repeat> parents do not change membership.
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
                    # translations follow; _apply_translations continues this iterator
                    break
                continue

            if elem.tag == ns_channel:
                open_channel = None
            elif elem.tag == ns_module_def:
                module_stack.pop()
            elem.clear()

        if identity is None:
            raise UnexpectedDataError("ApplicationProgram element not found")

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
        # ComObjectRef without ComObject. Every listed id must be a key of
        # `objects`, so these are logged and left out instead of exported.
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
        Add refs of module definitions to the channels instantiating the modules.

        channel_refs: Channel id -> refs inside the Channel in document order; the
            refs of the modules instantiated in the Channel are appended
        module_ids: ids of all ModuleDefs including SubModuleDefs, in document order
        module_refs: ModuleDef id -> refs in its Dynamic section outside its own
            Channels, in document order
        module_placements: (ModuleDef id, parent) of every `<Module>`
            instantiation, in document order
        independent_candidates: refs outside any Channel in document order, with
            the ModuleDef containing them (None outside ModuleDefs)

        A module instantiated inside another module inherits every placement of
        that module, recursively. The modules of a Channel are processed in the
        order of its `<Module>` elements and each adds its own refs, then those of
        its sub-modules. Modules reachable only through cyclic instantiation are
        treated as never instantiated.

        Return the channel independent refs in document order: refs outside any
        ModuleDef and refs of modules instantiated outside any Channel or never
        instantiated. A ref is both channel independent and a channel member when
        its module is instantiated both ways.
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
        # never instantiated modules: their refs are channel independent
        root_modules.extend(
            module_id for module_id in module_ids if module_id not in placed_modules
        )

        def _reach(module_id: str, reached: set[str]) -> list[str]:
            """Return a module and its sub-modules not in `reached` yet, depth first; add them to `reached`."""
            if module_id in reached:  # also guards cyclic instantiation
                return []
            reached.add(module_id)
            result = [module_id]
            for child_id in child_modules.get(module_id, {}):
                result.extend(_reach(child_id, reached))
            return result

        in_channel: set[str] = set()
        for channel_id, placed_module_ids in channel_modules.items():
            # one reached set per channel: a module instantiated twice in a channel
            # adds its refs once
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
        """
        Return the KIM version from the root Semantics attribute, None without one.

        Examples
        --------
        "# Serialization-Format-Version=2, KIM-Version=(<http://schema.knx.org/2020/ontology/v2>, 92, 60), ..." -> "92.60"
        None -> None

        """
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
        """
        Apply the translations of one language in place.

        Continue `tree_iterator` after the <Languages> start event and stop at the
        end of the requested <Language>. Name is applied to the identity, Text and
        FunctionText to ComObjects and ComObjectRefs, Text to Channels.
        Translations are applied before refs are merged with their ComObjects, so
        a ref's own Text still overrides the translated ComObject Text.
        """
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
                # the program's own element keeps its absolute id: nothing to remove
                ref_id = elem.get("RefId", "").removeprefix(prefix)
            elif in_language and ref_id is not None and elem.tag == ns_translation:
                attribute = elem.get("AttributeName")
                text = elem.get("Text")
                # an empty translation must not erase the default text
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
        """
        Merge every ComObjectRef with its ComObject into an ObjectDefinition.

        Attributes set on the ref win; unset ones (None, or no DatapointType) are
        taken from the ComObject. `number` is the ComObject number without a module
        base number, DPAs come from the ref only, and `channel_ids` lists the
        channels whose refs contain the ref. Refs whose ComObject is missing are
        skipped; `_load` logs them.
        """
        channel_ids_by_object: dict[str, list[str]] = {}
        for channel_id, refs in channel_refs.items():
            for object_id in refs:
                channel_ids_by_object.setdefault(object_id, []).append(channel_id)

        objects: dict[str, ObjectDefinition] = {}
        for ref_id, ref in com_object_refs.items():
            com_object = com_objects.get(ref.ref_id)
            if com_object is None:
                continue
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
                # an empty DatapointType on the ref inherits the ComObject's
                dpts=ref.datapoint_types or com_object.datapoint_types,
                flags=Flags(
                    read=_inherit(ref.read_flag, com_object.flags["read"]),
                    write=_inherit(ref.write_flag, com_object.flags["write"]),
                    communication=_inherit(
                        ref.communication_flag, com_object.flags["communication"]
                    ),
                    transmit=_inherit(ref.transmit_flag, com_object.flags["transmit"]),
                    update=_inherit(ref.update_flag, com_object.flags["update"]),
                    read_on_init=_inherit(
                        ref.read_on_init_flag, com_object.flags["read_on_init"]
                    ),
                ),
                # DPAs (Semantics) are read from ComObjectRefs only, as in
                # ApplicationProgramLoader
                dpas=ref.dpas,
                channel_ids=channel_ids_by_object.get(ref_id, []),
            )
        return objects
