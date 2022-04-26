"""Class to read KNXProj ZIP files."""
from __future__ import annotations

import base64
from os.path import exists
import shutil
from typing import Any
from zipfile import ZipFile, ZipInfo

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import pyzipper

from xknxproject.const import ETS6_SCHEMA_VERSION
from xknxproject.exceptions import InvalidPasswordException, ProjectNotFoundException


class KNXProjExtractor:
    """Class for reading a KNX Project file."""

    def __init__(
        self,
        archive_name: str,
        password: str | None = None,
        extraction_path: str = "/tmp/xknxproj/",
    ):
        """Initialize a KNXProjReader class."""
        self.archive_name = archive_name
        self.password = password
        self.extraction_path = extraction_path
        self._infos: list[ZipInfo] = []

    def get_project_id(self) -> str:
        """Get the project id."""
        for info in self._infos:
            if info.filename.startswith("P-") and info.filename.endswith(".signature"):
                return info.filename.removesuffix(".signature")

        raise ProjectNotFoundException()

    def __enter__(self) -> KNXProjExtractor:
        """Context manager enter."""
        self.extract()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.cleanup()

    def extract(self) -> None:
        """Read the ZIP file."""
        with ZipFile(self.archive_name) as zip_archive:
            zip_archive.extractall(self.extraction_path)
            self._infos = zip_archive.infolist()
            for info in self._infos:
                if ".zip" in info.filename and self.password:
                    self.unzip_protected_project_file(info)

        self._verify()

    def cleanup(self) -> None:
        """Cleanup the extracted files."""
        if exists(self.extraction_path):
            shutil.rmtree(self.extraction_path)

    def _verify(self) -> None:
        """Verify the extracted ETS files."""
        if not exists(self.extraction_path + self.get_project_id() + "/0.xml"):
            raise ProjectNotFoundException()

    def unzip_protected_project_file(self, info: ZipInfo) -> None:
        """Unzip a protected ETS5/6 project file."""
        if not self.password:
            raise InvalidPasswordException()

        if not self._is_project_ets6():
            try:
                with ZipFile(self.extraction_path + info.filename) as project_file:
                    project_file.extractall(
                        self.extraction_path + info.filename.replace(".zip", ""),
                        pwd=self.password.encode("utf-8"),
                    )
                return
            except Exception as exception:
                raise InvalidPasswordException from exception

        if self._is_project_ets6():
            try:
                with pyzipper.AESZipFile(self.extraction_path + info.filename) as file:
                    file.extractall(
                        self.extraction_path + info.filename.replace(".zip", ""),
                        pwd=self.generate_ets6_zip_password(),
                    )
            except Exception as exception:
                raise InvalidPasswordException from exception

    def _is_project_ets6(self) -> bool:
        """Check if the project is an ETS6 project."""
        with open(self.extraction_path + "knx_master.xml", encoding="utf-8") as master:
            for value in [next(master) for _ in range(2)]:
                if ETS6_SCHEMA_VERSION in value:
                    return True

        return False

    def generate_ets6_zip_password(self) -> bytes:
        """Generate ZIP archive password."""
        if not self.password:
            return bytes()

        return base64.b64encode(
            PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"21.project.ets.knx.org",
                iterations=65536,
            ).derive(self.password.encode("utf-16-le"))
        )
