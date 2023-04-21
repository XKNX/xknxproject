"""ETS Project Parser is a library to parse ETS project files."""
from __future__ import annotations

from pathlib import Path

from xknxproject import __version__
from xknxproject.models import KNXProject
from xknxproject.xml import XMLParser
from xknxproject.zip.extractor import extract


class XKNXProj:
    """Class for parsing ETS project files."""

    def __init__(
        self,
        path: str | Path,
        password: str | None = None,
        language: str | None = None,
    ):
        """Initialize a KNXProjParser."""
        self.path = Path(path)
        self.password = password
        self.language = language

        self.version = __version__

    def parse(self) -> KNXProject:
        """Parse the KNX project."""
        with extract(self.path, self.password) as knx_project_content:
            return XMLParser(knx_project_content).parse(self.language)
