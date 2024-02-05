"""XML utilities."""
from __future__ import annotations

import logging
from typing import overload

from xknxproject.const import MAIN_AND_SUB_DPT, MAIN_DPT
from xknxproject.models import DPTType

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
def parse_xml_flag(flag: str | None, default: bool) -> bool:
    ...


@overload
def parse_xml_flag(flag: str | None, default: None = None) -> bool | None:
    ...


def parse_xml_flag(flag: str | None, default: bool | None = None) -> bool | None:
    """Parse the XML flag to an optional boolean."""
    if flag is None:
        return default
    return flag == "Enabled"
