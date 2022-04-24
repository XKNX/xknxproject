"""Class to read KNXProj ZIP files."""
from __future__ import annotations

from os.path import exists
import shutil
from zipfile import ZipFile, ZipInfo


class KNXProjExtractor:
    """Class for reading a KNX Project file."""

    extraction_path = "/tmp/xknxproj/"

    def __init__(self, archive_name: str, password: str | None = None):
        """Initialize a KNXProjReader class."""
        self.archive_name = archive_name
        self.password = password

    def extract(self) -> None:
        """Read the ZIP file."""
        with ZipFile(self.archive_name) as zip_archive:
            zip_archive.extractall(self.extraction_path)
            infos: list[ZipInfo] = zip_archive.infolist()
            for info in infos:
                if ".zip" in info.filename and self.password:
                    with ZipFile(self.extraction_path + info.filename) as project_file:
                        project_file.extractall(
                            self.extraction_path + info.filename.replace(".zip", ""),
                            pwd=self.password.encode("utf-8"),
                        )

    def cleanup(self) -> None:
        """Cleanup the extracted files."""
        if exists(self.extraction_path):
            shutil.rmtree(self.extraction_path)
