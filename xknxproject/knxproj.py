"""ETS Project Parser is a library to parse ETS project files."""
from __future__ import annotations

import logging

from xknxproject import __version__
from xknxproject.zip import KNXProjExtractor

logger = logging.getLogger("xknxproject.log")


class KNXProjParser:
    """Class for parsing ETS project files."""

    def __init__(self, archive_name: str, archive_password: str | None = None):
        """Initialize a KNXProjParser."""
        self.reader = KNXProjExtractor(archive_name, archive_password)
        self.version = __version__
