"""XML utilities."""
from __future__ import annotations

import logging
from typing import overload

from xknxproject.const import MAIN_AND_SUB_DPT, MAIN_DPT
from xknxproject.models import DPTType

_LOGGER = logging.getLogger("xknxproject.log")


def parse_dpt_types(dpt: str | None) -> DPTType | None:
    """Parse the DPT types from the XML representation to main and sub types."""
    if not dpt:
        return None

    dpt_type: str = dpt.split(" ")[-1]
    if MAIN_DPT in dpt_type:
        return DPTType(
            main=int(dpt_type.split("-")[1]),
            sub=None,
        )
    if MAIN_AND_SUB_DPT in dpt_type:
        return DPTType(
            main=int(dpt_type.split("-")[1]),
            sub=int(dpt_type.split("-")[2]),
        )
    _LOGGER.warning('Could not parse DPTType from: "%s"', dpt_type)
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
