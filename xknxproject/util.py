"""XML utilities."""
from __future__ import annotations

import logging
from typing import overload

from xknxproject.const import MAIN_AND_SUB_DPT, MAIN_DPT
from xknxproject.models import DPTType

_LOGGER = logging.getLogger("xknxproject.log")


def parse_dpt_type(dpt_string: str | None) -> DPTType | None:
    """Parse a DPT type from the XML representation to main and sub types."""
    if not dpt_string:
        return None

    last_dpt: str = dpt_string.split(" ")[-1]
    dpt_parts = last_dpt.split("-")
    try:
        if MAIN_DPT == dpt_parts[0]:
            return DPTType(
                main=int(dpt_parts[1]),
                sub=None,
            )
        if MAIN_AND_SUB_DPT == dpt_parts[0]:
            return DPTType(
                main=int(dpt_parts[1]),
                sub=int(dpt_parts[2]),
            )
    except (IndexError, ValueError):
        pass
    _LOGGER.warning('Could not parse DPTType from: "%s"', dpt_string)
    return None


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
