"""ETS Project Parser is a library to parse ETS project files."""

from __future__ import annotations

import logging
from pathlib import Path
import time

from xknxproject.__version__ import __version__
from xknxproject.combination import combine_project
from xknxproject.models import KNXProject
from xknxproject.xml import XMLParser
from xknxproject.zip.extractor import extract

_LOGGER = logging.getLogger("xknxproject.log")


class XKNXProj:
    """Class for parsing ETS project files."""

    def __init__(
        self,
        path: str | Path,
        password: str | None = None,
        language: str | None = None,
    ) -> None:
        """Initialize a KNXProjParser."""
        self.path = Path(path)
        self.password = password
        self.language = language

    def parse(self, combine: bool = True) -> KNXProject:
        """Parse the KNX project."""
        _LOGGER.info(
            'Xknxproject version %s parsing "%s" with%s password...',
            __version__,
            self.path,
            "" if self.password else "out",
        )
        _start = time.time()
        with extract(self.path, self.password) as knx_project_content:
            project = XMLParser(knx_project_content).parse(self.language)

        if combine:
            project = combine_project(project)

        _LOGGER.info("Parsing took %s seconds", time.time() - _start)
        _LOGGER.info(
            "Found %s group addresses, %s devices and %s used communication objects",
            len(project["group_addresses"]),
            len(project["devices"]),
            len(project["communication_objects"]),
        )
        return project
