"""XML utilities."""
from __future__ import annotations

from typing import Any
from xml.dom.minidom import Attr


def attr(attribute: Any | Attr) -> Any:
    """Return the attribute value or None."""
    if isinstance(attribute, Attr):
        return attribute.value

    return attribute
