"""XML utilities."""
from __future__ import annotations

from typing import Any
from xml.dom.minidom import Attr, Document


def attr(attribute: Any | Attr) -> Any:
    """Return the attribute value or None."""
    if isinstance(attribute, Attr):
        return attribute.value

    return attribute


def child_nodes(root_node: Document) -> list[Document]:
    """Get child nodes without line breaks from node."""
    return [node for node in root_node.childNodes if node.nodeType != 3]


def flatten(to_flat: list[Any]) -> list[Any]:
    """Flatten a given list."""
    return [item for sublist in to_flat for item in sublist]
