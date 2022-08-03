"""XML utilities."""
from xknxproject.const import MAIN_AND_SUB_DPT, MAIN_DPT


def parse_dpt_types(dpt_types: list[str]) -> dict[str, int]:
    """Parse the DPT types from the KNX project to main and sub types."""
    if len(dpt_types) == 0:
        return {}

    dpt_type: str = dpt_types[len(dpt_types) - 1]
    if MAIN_DPT in dpt_type:
        return {"main": int(dpt_type.split("-")[1])}
    if MAIN_AND_SUB_DPT in dpt_type:
        return {"main": int(dpt_type.split("-")[1]), "sub": int(dpt_type.split("-")[2])}

    return {}
