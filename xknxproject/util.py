"""XML utilities."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, overload

from xknxproject.const import MAIN_AND_SUB_DPT, MAIN_DPT
from xknxproject.exceptions import UnexpectedDataError
from xknxproject.models import DPTType

if TYPE_CHECKING:
    from xknxproject.models import ParameterInstanceRef

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
