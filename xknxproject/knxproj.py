"""ETS Project Parser is a library to parse ETS project files."""
from __future__ import annotations

import logging

from xknxproject import __version__
from xknxproject.models import Area, GroupAddress
from xknxproject.xml import XMLParser
from xknxproject.zip import KNXProjExtractor

logger = logging.getLogger("xknxproject.log")


class KNXProj:
    """Class for parsing ETS project files."""

    def __init__(self, archive_name: str, archive_password: str | None = None):
        """Initialize a KNXProjParser."""
        self.extractor = KNXProjExtractor(archive_name, archive_password)
        self.parser = XMLParser(self.extractor)
        self.version = __version__

    async def parse(self) -> tuple[list[Area], list[GroupAddress]]:
        """Parse the KNX project."""
        with self.extractor:
            await self.parser.parse()
        return self.parser.areas, self.parser.group_addresses
