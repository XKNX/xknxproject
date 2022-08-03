"""Class to read KNXProj ZIP files."""
from __future__ import annotations

import base64
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO
from zipfile import Path as ZipPath, ZipFile, ZipInfo

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import pyzipper

from xknxproject.const import ETS6_SCHEMA_VERSION
from xknxproject.exceptions import InvalidPasswordException, ProjectNotFoundException


class KNXProjContents:
    """Class for holding the contents of a KNXProj file."""

    def __init__(
        self, root_zip: ZipFile, project_0_archive: ZipFile, project_0_name: str
    ):
        """Initialize a KNXProjContents."""
        self._project_0_archive = project_0_archive
        self._project_0_name = project_0_name
        self.root = root_zip
        self.root_path = ZipPath(root_zip)

    def open_project_0(self) -> IO[bytes]:
        """Open the project 0 archive."""
        return self._project_0_archive.open(self._project_0_name, mode="r")


@contextmanager
def extract(
    archive_path: Path, password: str | None = None
) -> Iterator[KNXProjContents]:
    """Provide the contents of a KNXProj file."""
    with ZipFile(archive_path, mode="r") as zip_archive:
        project_id = _get_project_id(zip_archive)
        password_protected: bool
        try:
            protected_info = zip_archive.getinfo(name=project_id + ".zip")
        except KeyError:
            password_protected = False
        else:
            password_protected = True

        if not password_protected:
            project_0_name = f"{project_id}/0.xml"
            yield KNXProjContents(zip_archive, zip_archive, project_0_name)
            return
        # Password protected project
        with _extract_protected_project_file(
            zip_archive, protected_info, password
        ) as project_zip:
            # ZipPath is not supported by pyzipper thus we use string name
            project_0_name = "0.xml"
            yield KNXProjContents(zip_archive, project_zip, project_0_name)


def _get_project_id(zip_archive: ZipFile) -> str:
    """Get the project id."""
    for info in zip_archive.infolist():
        if info.filename.startswith("P-") and info.filename.endswith(".signature"):
            return info.filename.removesuffix(".signature")

    raise ProjectNotFoundException()


@contextmanager
def _extract_protected_project_file(
    archive_zip: ZipFile, info: ZipInfo, password: str | None
) -> Iterator[ZipFile]:
    """Unzip a protected ETS5/6 project file."""
    if not password:
        raise InvalidPasswordException()

    project_archive: ZipFile
    if not _is_ets6_project(archive_zip):
        try:
            project_archive = ZipFile(archive_zip.open(info, mode="r"), mode="r")
            project_archive.setpassword(password.encode("utf-8"))
            yield project_archive
        except RuntimeError as exception:
            raise InvalidPasswordException from exception
    else:
        try:
            project_archive = pyzipper.AESZipFile(
                archive_zip.open(info, mode="r"), mode="r"
            )
            project_archive.setpassword(_generate_ets6_zip_password(password))
            yield project_archive
        except RuntimeError as exception:
            raise InvalidPasswordException from exception


def _is_ets6_project(project_zip: ZipFile) -> bool:
    """Check if the project is an ETS6 project."""
    with project_zip.open("knx_master.xml", mode="r") as master:
        for line in [next(master) for _ in range(2)]:
            if ETS6_SCHEMA_VERSION in line:
                return True

    return False


def _generate_ets6_zip_password(password: str | None) -> bytes:
    """Generate ZIP archive password."""
    if not password:
        return b""

    return base64.b64encode(
        PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"21.project.ets.knx.org",
            iterations=65536,
        ).derive(password.encode("utf-16-le"))
    )
