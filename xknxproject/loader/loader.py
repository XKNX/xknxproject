"""XML Loader for knxproj XML model data."""
import abc
from typing import Any


class XMLLoader(abc.ABC):
    """XML Loader that handles loading different KNX XML elements."""

    @abc.abstractmethod
    async def load(self, extraction_path: str) -> list[Any]:
        """Load via the given loader implementation."""
