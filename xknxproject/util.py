"""XML utilities."""
from __future__ import annotations

from typing import overload

from xknxproject.const import MAIN_AND_SUB_DPT, MAIN_DPT


def parse_dpt_types(dpt_types: list[str]) -> dict[str, int]:
    """Parse the DPT types from the KNX project to main and sub types."""
    if len(dpt_types) == 0:
        return {}

    dpt_type: str = dpt_types[-1]
    if MAIN_DPT in dpt_type:
        return {"main": int(dpt_type.split("-")[1])}
    if MAIN_AND_SUB_DPT in dpt_type:
        return {"main": int(dpt_type.split("-")[1]), "sub": int(dpt_type.split("-")[2])}

    return {}


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
