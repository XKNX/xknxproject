"""XML utilities."""
from __future__ import annotations

from typing import Any
from xml.dom.minidom import Attr, Document

from xknxproject.const import MAIN_AND_SUB_DPT, MAIN_DPT


def attr(attribute: Any | Attr) -> Any:
    """Return the attribute value or None."""
    if isinstance(attribute, Attr):
        return attribute.value

    return attribute


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


def child_nodes(root_node: Document) -> list[Document]:
    """Get child nodes without line breaks from node."""
    return [node for node in root_node.childNodes if node.nodeType != 3]


def flatten(to_flat: list[Any]) -> list[Any]:
    """Flatten a given list."""
    return [item for sublist in to_flat for item in sublist]
