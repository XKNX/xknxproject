"""XML utilities."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Literal, overload

from xknxproject.const import MAIN_AND_SUB_DPT, MAIN_DPT
from xknxproject.exceptions import UnexpectedDataError
from xknxproject.models import DPTType

if TYPE_CHECKING:
    from xknxproject.models import (
        ApplicationProgramDefinition,
        KNXProject,
        ObjectDefinition,
        ParameterInstanceRef,
    )

_LOGGER = logging.getLogger("xknxproject.log")


def get_dpt_type(dpt_string: str | None) -> DPTType | None:
    """Parse DPT type from the XML representation to main and sub types."""
    # GroupAddress tags should only support one single DPT.
    try:
        return parse_dpt_types(dpt_string)[0]
    except IndexError:
        return None


def parse_dpt_types(dpt_string: str | None) -> list[DPTType]:
    """Parse all DPTs from the XML representation to main and sub types."""
    if not dpt_string:
        return []

    supported_dpts: list[DPTType] = []
    # some applications have listed same DPT multiple times `DatapointType="DPST-1-1 DPST-1-1"`
    # so we use dict.fromkeys() (as set() doesn't preserve order)
    for _dpt in dict.fromkeys(dpt_string.split()):
        dpt_parts = _dpt.split("-")
        try:
            if dpt_parts[0] == MAIN_DPT:
                supported_dpts.append(
                    DPTType(
                        main=int(dpt_parts[1]),
                        sub=None,
                    )
                )
            if dpt_parts[0] == MAIN_AND_SUB_DPT:
                supported_dpts.append(
                    DPTType(
                        main=int(dpt_parts[1]),
                        sub=int(dpt_parts[2]),
                    )
                )
        except (IndexError, ValueError):
            _LOGGER.warning(
                'Could not parse DPTType from: "%s" in "%s"', _dpt, dpt_string
            )
    return supported_dpts


def parse_semantics_functional_blocks(semantic_string: str | None) -> list[str] | None:
    """Parse functional blocks from the XML representation."""
    # example for Channel: Semantics="knx:fb.417"
    if not semantic_string:
        return None

    # unique with preserved order, value is not used
    functional_blocks: dict[str, None] = {}
    for fb in semantic_string.split():
        try:
            fb_string = fb.removeprefix("knx:fb.")
            int(fb_string)  # check for int - we don't need the value
            functional_blocks[fb_string] = None
        except ValueError:
            _LOGGER.warning(
                'Could not parse functional block from: "%s" in "%s"',
                fb,
                semantic_string,
            )
            continue
    return list(functional_blocks.keys()) or None


def parse_semantics_dpas(semantic_string: str | None) -> list[str] | None:
    """Parse DPAs from the XML representation."""
    if not semantic_string:
        return None

    # unique with preserved order, value is not used
    dpas: dict[str, None] = {}
    for dpa in semantic_string.split():
        try:
            dpa_id = dpa.removeprefix("knx:dpa.")
            # check for "." separated integers - we don't need the values
            _fb, _dpa_num = map(int, dpa_id.split(".", 1))
            dpas[dpa_id] = None
        except ValueError:
            _LOGGER.warning(
                'Could not parse DPA from: "%s" in "%s"', dpa, semantic_string
            )
            continue
    return list(dpas.keys()) or None


@overload
def parse_xml_flag(flag: str | None, default: bool) -> bool: ...


@overload
def parse_xml_flag(flag: str | None, default: None = None) -> bool | None: ...


def parse_xml_flag(flag: str | None, default: bool | None = None) -> bool | None:
    """Parse the XML flag to an optional boolean."""
    if flag is None:
        return default
    return flag == "Enabled"


def text_parameter_template_replace(
    text: str, parameter: ParameterInstanceRef | None
) -> str:
    """Replace parameter template in text."""
    # Text of a Channel, ParameterBlock, ParameterSeparator, ParameterRef or ComObjectRef
    # may use placeholder "{{0}}" or "{{0:def}}" (without the quotes). def is a default
    # text to be displayed if the text parameter value is empty.
    # These placeholders (with or without the default text) are included in translations too.

    # Applications TextParameterRef points to 0.xml ParameterInstanceRef of DeviceInstance

    parameter_value = parameter.value if parameter is not None else None
    return re.sub(
        r"{{0(?::?)(.*?)}}",
        lambda matchobj: parameter_value or matchobj.group(1),
        text,
    )


def strip_module_instance(text: str, search_id: str) -> str:
    """
    Remove module and module instance from text, keep module definition and rest.

    text: full text to be processed
    search_id: search term to be kept without "-" eg. "CH" for channel

    Examples
    --------
    search_id="CH": "CH-4" -> "CH-4"
    search_id="CH": "MD-1_M-1_MI-1_CH-4" -> "MD-1_CH-4"
    search_id="O": "MD-4_M-15_MI-1_SM-1_M-1_MI-1-1-2_SM-1_O-3-1_R-2" -> "MD-4_SM-1_O-3-1_R-2"

    """
    # For submodules SM- must be the last item before search_id
    # because I couldn't create a regex that works otherwise :(
    return re.sub(
        r"(MD-\w+_)?.*?(SM-\w+_)?(" + re.escape(search_id) + r"-.*)",
        lambda matchobj: "".join(part for part in matchobj.groups() if part),
        text,
    )


def get_module_instance_part(ref: str, next_id: str) -> str:
    """
    Get module and module instance from text or empty string if not found.

    ref: full text to be processed
    next_id: search term after module definitions. Eg. "CH" for channel

    """
    # For submodules SM- must be the last item before search_id
    # because I couldn't create a regex that works otherwise :(

    matchobj = re.search(r"(MD-.*)_" + re.escape(next_id) + r"-", ref)
    return matchobj.group(1) if matchobj else ""


def text_parameter_insert_module_instance(
    instance_ref: str, instance_next_id: str, text_parameter_ref_id: str
) -> str:
    """
    Insert module and module instance from instance_ref into target_ref.

    instance_ref: reference holding module instance
    instance_next_id: search term after module definitions. Eg. "CH" for channel
    text_parameter_ref_id: reference with module definition where module instance
      should be inserted after module definition
    """
    if "_MD-" in text_parameter_ref_id and (
        _module_ref := get_module_instance_part(instance_ref, next_id=instance_next_id)
    ):
        _application_ref = text_parameter_ref_id.split("_MD-", maxsplit=1)[0]
        try:
            # `_P-` for Parameter `_UP-` for UnionParameter
            _parameter_ref = re.search(r"_(U?P-.*)", text_parameter_ref_id).group(1)  # type: ignore[union-attr]
        except AttributeError:
            raise UnexpectedDataError(
                f"No Parameter block found in TextParameterRefId {text_parameter_ref_id} "
                f"(instance: {instance_ref})"
            ) from None
        return f"{_application_ref}_{_module_ref}_{_parameter_ref}"

    return text_parameter_ref_id


# "M-0008_A-20E0-21-9997-O000A": manufacturer, program part, optional original manufacturer.
# The "-O" suffix is matched case-insensitively and only with 4 hex digits; otherwise it
# stays part of the program part. Shared with the application program parser.
_APPLICATION_ID_RE = re.compile(
    r"^(?P<manufacturer>M-[0-9A-Fa-f]{4})_A-(?P<program>.+?)(?:-[Oo](?P<oem>[0-9A-Fa-f]{4}))?$"
)


def application_id_original_manufacturer(application_id: str) -> str | None:
    """
    Return the original manufacturer of the "-Oxxxx" suffix of an application id.

    Return None if the id has no such suffix.

    Examples
    --------
    "M-0008_A-20E0-21-9997-O000A" -> "M-000A"
    "M-0083_A-013A-32-DCC1" -> None

    """
    match = _APPLICATION_ID_RE.match(application_id)
    if match is None or not match["oem"]:
        return None
    return f"M-{match['oem'].upper()}"


def canonical_application_id(
    application_id: str, original_manufacturer_id: str | None
) -> str:
    """
    Return the id of an application program independent of rebranding.

    Programs of OEM products carry the id of the selling manufacturer and the
    original manufacturer as "-Oxxxx" suffix. The canonical id names the
    original manufacturer and drops the suffix, so rebranded copies of one
    program share it. Ids not following the pattern are returned unchanged.

    Examples
    --------
    "M-0008_A-20E0-21-9997-O000A" -> "M-000A_A-20E0-21-9997"
    "M-0083_A-013A-32-DCC1" -> "M-0083_A-013A-32-DCC1"

    """
    match = _APPLICATION_ID_RE.match(application_id)
    if match is None:
        return application_id
    manufacturer = (
        original_manufacturer_id
        or application_id_original_manufacturer(application_id)
        or match["manufacturer"]
    )
    return f"{manufacturer.upper()}_A-{match['program']}"


def instance_definition_id(
    instance_id: str, application_id: str, search_id: Literal["CH", "O"]
) -> str:
    """
    Return the definition id of a channel or object instance of a project.

    instance_id: id of a channel or communication object instance as `parse()`
        returns it, with or without the device address ("1.1.1/...")
    application_id: id of the application program of the device
    search_id: "CH" for channels, "O" for objects

    The module instance parts are removed (see `strip_module_instance`) and so
    is the application id older projects prefix the id with; the result is a
    key of `channels` or `objects` of the program's definition.

    Examples
    --------
    "1.1.1/MD-2_M-1_MI-1_O-2-1_R-1" -> "MD-2_O-2-1_R-1"
    "M-0083_A-013A-32-DCC1_O-1_R-1" -> "O-1_R-1"

    """
    instance_part = instance_id.split("/", maxsplit=1)[-1]
    # the module part of `strip_module_instance` is only recognized at the start
    instance_part = instance_part.removeprefix(f"{application_id}_")
    return strip_module_instance(instance_part, search_id=search_id)


def _object_module(object_definition: ObjectDefinition) -> str | None:
    """Return the module an object is defined in, None outside modules."""
    identifier = object_definition["identifier"]
    return identifier.split("_O-", maxsplit=1)[0] if "_O-" in identifier else None


def _in_module(object_module: str, module: str) -> bool:
    """Check if an object module is a module or one of its submodules."""
    return object_module == module or object_module.startswith(f"{module}_SM-")


def object_channel_id(
    definition: ApplicationProgramDefinition, object_definition: ObjectDefinition
) -> str | None:
    """
    Return the channel an object definition belongs to, None without one.

    An object listed by several channels - a module instantiated in a channel -
    belongs to the channel whose `module_definition_id` equals the module of
    the object or is the module whose submodule (`<module>_SM-...`) defines the
    object; an object outside modules belongs to a channel outside modules.
    Without such a channel the first listed channel that exists is returned.
    """
    object_module = _object_module(object_definition)
    channels = [
        (channel_id, channel)
        for channel_id in object_definition["channel_ids"]
        if (channel := definition["channels"].get(channel_id)) is not None
    ]
    for channel_id, channel in channels:
        module = channel["module_definition_id"]
        if (
            module is None
            if object_module is None
            else module is not None and _in_module(object_module, module)
        ):
            return channel_id
    return channels[0][0] if channels else None


def linked_object_definitions(project: KNXProject) -> dict[str, set[str]]:
    """
    Return the object definitions devices link to group addresses, by program.

    Keys are application program ids; programs whose devices link no object
    are left out.
    """
    objects = project["communication_objects"]
    linked: dict[str, set[str]] = {}
    for device in project["devices"].values():
        if (application_id := device["application"]) is None:
            continue
        for object_id in device["communication_object_ids"]:
            com_object = objects.get(object_id)
            if com_object is not None and com_object["group_address_links"]:
                linked.setdefault(application_id, set()).add(
                    instance_definition_id(object_id, application_id, "O")
                )
    return linked
