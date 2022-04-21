"""ETS Project Parser is a library to parse ETS project files."""
from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
import os

logger = logging.getLogger("xknx.log")


class ETSProjectParser:
    """Class for parsing ETS project files."""

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
            "ets.log",
        ]:
            _logger = logging.getLogger(log_namespace)
            _logger.addHandler(_handler)
