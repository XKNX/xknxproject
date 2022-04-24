"""ETS Project Parser is a library to parse ETS project files."""
from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
import os

from xknxproject.zip import KNXProjExtractor

logger = logging.getLogger("xknxproject.log")


class KNXProjParser:
    """Class for parsing ETS project files."""

    def __init__(self, archive_name: str, archive_password: str | None = None):
        """Initialize a KNXProjParser."""
        self.reader = KNXProjExtractor(archive_name, archive_password)

    @staticmethod
    def setup_logging(log_directory: str) -> None:
        """Configure logging to file."""
        if not os.path.isdir(log_directory):
            logger.warning("The provided log directory does not exist.")
            return

        _handler = TimedRotatingFileHandler(
            filename=f"{log_directory}{os.sep}ets.log",
            when="midnight",
            backupCount=7,
            encoding="utf-8",
        )
        _formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        _handler.setFormatter(_formatter)
        _handler.setLevel(logging.DEBUG)

        for log_namespace in [
            "xknxproject.log",
        ]:
            _logger = logging.getLogger(log_namespace)
            _logger.addHandler(_handler)
