"""Class to read KNXProj ZIP files."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from contextlib import contextmanager
import hashlib
import logging
from pathlib import Path
import re
from typing import IO
from zipfile import Path as ZipPath, ZipFile, ZipInfo

import pyzipper

from xknxproject.const import ETS_4_2_SCHEMA_VERSION, ETS_6_SCHEMA_VERSION
from xknxproject.exceptions import (
    InvalidPasswordException,
    ProjectNotFoundException,
    UnexpectedFileContent,
)

_LOGGER = logging.getLogger("xknxproject.log")


class KNXProjContents:
    """Class for holding the contents of a KNXProj file."""

    def __init__(
        self,
        root_zip: ZipFile,
        project_archive: ZipFile,
        project_relative_path: str,
        xml_namespace: str,
    ) -> None:
        """Initialize a KNXProjContents."""
        self._project_archive = project_archive
        self._project_relative_path = project_relative_path
        self.root = root_zip
        self.root_path = ZipPath(root_zip)
        self.xml_namespace = xml_namespace
        self.schema_version = _get_schema_version(xml_namespace)

    def is_ets4_project(self) -> bool:
        """Check if the project is an ETS4 project."""
        return self.schema_version <= ETS_4_2_SCHEMA_VERSION

    def open_project_0(self) -> IO[bytes]:
        """Open the project 0.xml file."""
        return self._project_archive.open(
            f"{self._project_relative_path}0.xml",
            mode="r",
        )

    def open_project_meta(self) -> IO[bytes]:
        """Open the project.xml file."""
        project_filename = "Project.xml" if self.is_ets4_project() else "project.xml"
        return self._project_archive.open(
            f"{self._project_relative_path}{project_filename}",
            mode="r",
        )


@contextmanager
def extract(
    archive_path: Path, password: str | None = None
) -> Iterator[KNXProjContents]:
    """Provide the contents of a KNXProj file."""
    _LOGGER.debug('Opening KNX Project file "%s"', archive_path)
    with ZipFile(archive_path, mode="r") as zip_archive:
        project_id = _get_project_id(zip_archive)
        xml_namespace = _get_xml_namespace(zip_archive)

        password_protected: bool
        try:
            protected_info = zip_archive.getinfo(name=project_id + ".zip")
        except KeyError:
            _LOGGER.debug("Project %s is not password protected", project_id)
            password_protected = False
            # move yield out of except block to clear exception context
        else:
            _LOGGER.debug("Project %s is password protected", project_id)
            password_protected = True

        if not password_protected:
            yield KNXProjContents(
                root_zip=zip_archive,
                project_archive=zip_archive,
                project_relative_path=f"{project_id}/",
                xml_namespace=xml_namespace,
            )
            return
        # Password protected project
        schema_version = _get_schema_version(xml_namespace)
        with _extract_protected_project_file(
            zip_archive, protected_info, password, schema_version
        ) as project_zip:
            # ZipPath is not supported by pyzipper thus we use
            # string name for project_relative_path
            yield KNXProjContents(
                root_zip=zip_archive,
                project_archive=project_zip,
                project_relative_path="",
                xml_namespace=xml_namespace,
            )


def _get_project_id(zip_archive: ZipFile) -> str:
    """Get the project id."""
    for info in zip_archive.infolist():
        if info.filename.startswith("P-") and info.filename.endswith(".signature"):
            return info.filename.removesuffix(".signature")

    raise ProjectNotFoundException("Signature file not found.")


@contextmanager
def _extract_protected_project_file(
    archive_zip: ZipFile, info: ZipInfo, password: str | None, schema_version: int
) -> Iterator[ZipFile]:
    """Unzip a protected ETS5/6 project file."""
    if not password:
        raise InvalidPasswordException("Password required.")

    try:
        project_archive: ZipFile
        pwd: bytes
        # Password protection is different for ETS4/5 and ETS6
        project_archive_file = archive_zip.open(info, mode="r")
        if schema_version < ETS_6_SCHEMA_VERSION:
            project_archive = ZipFile(project_archive_file, mode="r")
            pwd = password.encode("utf-8")
        else:
            project_archive = pyzipper.AESZipFile(project_archive_file, mode="r")
            pwd = _generate_ets6_zip_password(password)
        project_archive.setpassword(pwd)
        yield project_archive
    except RuntimeError as exception:
        raise InvalidPasswordException("Invalid password.") from exception
    finally:
        _LOGGER.debug("Closed protected project archive")
        project_archive_file.close()


def _get_xml_namespace(project_zip: ZipFile) -> str:
    """Get the XML namespace of the project."""
    with project_zip.open("knx_master.xml", mode="r") as master:
        for line_number, line in enumerate(master, start=1):
            # ETS 4.1 has namespace in the first line, newer versions in second
            if line_number in (1, 2):
                try:
                    namespace_match = re.match(
                        r".+ xmlns=\"(.+?)\"",
                        line.decode(),
                    )
                    if namespace_match is None and line_number == 1:
                        continue
                    namespace = namespace_match.group(1)  # type: ignore[union-attr]
                    _LOGGER.debug("Namespace: %s", namespace)
                    return namespace
                except (AttributeError, IndexError, UnicodeDecodeError):
                    _LOGGER.error("Could not parse XML namespace from %s", line)
                    raise UnexpectedFileContent(
                        "Could not parse XML namespace."
                    ) from None
            else:
                break
        raise UnexpectedFileContent("Could not find XML namespace.")


def _get_schema_version(namespace: str) -> int:
    """Get the schema version of the project."""
    try:
        schema_version = int(namespace.rsplit("/", 1)[-1])
    except ValueError:
        _LOGGER.error("Could not parse schema version from %s", namespace)
        raise UnexpectedFileContent("Could not parse schema version.") from None

    _LOGGER.debug("Schema version: %s", schema_version)
    return schema_version


def _generate_ets6_zip_password(password: str) -> bytes:
    """Generate ZIP archive password."""

    return base64.b64encode(
        hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=password.encode("utf-16-le"),
            salt=b"21.project.ets.knx.org",
            iterations=65536,
            dklen=32,
        )
    )


# M-XXXX/....._A-....xml (application program),
# excluding Catalog/Hardware and Baggages subdirectories
_APPLICATION_PROGRAM_RE = re.compile(r"^M-[0-9A-Fa-f]{4}/[^/]*_A-[^/]*\.xml$")


class KNXProdContents:
    """Class for holding the contents of a KNXProd (``.knxprod``) file."""

    def __init__(
        self,
        root_zip: ZipFile,
        manufacturer_id: str,
        xml_namespace: str,
    ) -> None:
        """Initialize a KNXProdContents."""
        self.root = root_zip
        self.manufacturer_id = manufacturer_id
        self.xml_namespace = xml_namespace
        self.schema_version = _get_schema_version(xml_namespace)

    def application_program_paths(self) -> list[ZipPath]:
        """Return the application-program XML files in the archive."""
        return [
            ZipPath(self.root, at=info.filename)
            for info in self.root.infolist()
            if _APPLICATION_PROGRAM_RE.match(info.filename)
        ]


@contextmanager
def extract_prod(archive_path: Path) -> Iterator[KNXProdContents]:
    """Provide the contents of a ``.knxprod`` product file."""
    _LOGGER.debug('Opening KNX product file "%s"', archive_path)
    with ZipFile(archive_path, mode="r") as zip_archive:
        yield KNXProdContents(
            root_zip=zip_archive,
            manufacturer_id=_get_manufacturer_id(zip_archive),
            xml_namespace=_get_xml_namespace(zip_archive),  # reads knx_master.xml
        )


def _get_manufacturer_id(zip_archive: ZipFile) -> str:
    """Return the manufacturer id (``M-XXXX``) from the signature marker."""
    for info in zip_archive.infolist():
        if info.filename.startswith("M-") and info.filename.endswith(".signature"):
            return info.filename.removesuffix(".signature")
    raise ProjectNotFoundException("Manufacturer signature file not found.")
