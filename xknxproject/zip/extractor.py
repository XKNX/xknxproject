"""Class to read KNXProj ZIP files."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from contextlib import contextmanager
import hashlib
import io
import logging
from pathlib import Path
import re
import sys
from typing import IO, Any, Literal, overload
from zipfile import BadZipFile, Path as ZipPath, ZipFile, ZipInfo
import zlib

import pyzipper

from xknxproject.const import ETS_4_2_SCHEMA_VERSION, ETS_6_SCHEMA_VERSION
from xknxproject.exceptions import (
    InvalidPasswordException,
    InvalidProjectArchive,
    ProjectNotFoundException,
    UnexpectedFileContent,
)

if sys.version_info >= (3, 11):
    from importlib.resources.abc import Traversable
else:
    # the location before Python 3.11
    from importlib.abc import Traversable  # pylint: disable=deprecated-class

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
        self.root = root_zip
        self.root_path = ZipPath(root_zip)
        # the project folder - in the root archive, or the root of a protected
        # project's nested archive
        self.project_path: Traversable = ArchivePath(
            project_archive, project_relative_path
        )
        self.xml_namespace = xml_namespace
        self.schema_version = _get_schema_version(xml_namespace)

    def is_ets4_project(self) -> bool:
        """Check if the project is an ETS4 project."""
        return self.schema_version <= ETS_4_2_SCHEMA_VERSION

    def open_project_0(self) -> IO[bytes]:
        """Open the project 0.xml file."""
        return (self.project_path / "0.xml").open(mode="rb")

    def open_project_meta(self) -> IO[bytes]:
        """Open the project.xml file (Project.xml up to schema version 11)."""
        project_filename = "Project.xml" if self.is_ets4_project() else "project.xml"
        return (self.project_path / project_filename).open(mode="rb")


class ArchivePath(Traversable):
    """
    A file or folder inside a ZIP archive, as a `Traversable` like `zipfile.Path`.

    Works with archives of `zipfile` and of `pyzipper` (the AES encrypted archive
    of a protected project from schema version 21 on), which `zipfile.Path` can't
    wrap, as it only relies on `namelist()`, `getinfo()` and `open()`. Names are
    case-sensitive and use "/" as separator, eg. "BinaryData/<name>.dat".
    Consumers should rely on the `Traversable` protocol only, so the class can be
    replaced by another implementation of it.
    """

    def __init__(self, archive: ZipFile, at: str = "") -> None:
        """Initialize an ArchivePath for the member `at` of `archive`."""
        self._archive = archive
        self._at = at.strip("/")

    @property
    def name(self) -> str:
        """Return the last part of the path."""
        return self._at.rpartition("/")[2]

    def joinpath(self, *descendants: str) -> ArchivePath:
        """Return the path of `descendants` in this folder."""
        return ArchivePath(self._archive, "/".join((self._at, *descendants)))

    def __repr__(self) -> str:
        """Return a representation of the path."""
        return f"ArchivePath({self._at!r})"

    def is_file(self) -> bool:
        """Return whether the path is a file in the archive."""
        if not self._at:
            return False
        try:
            self._archive.getinfo(self._at)
        except KeyError:
            return False
        return True

    def is_dir(self) -> bool:
        """Return whether the path is a folder (with or without an entry of its own)."""
        return not self._at or any(
            name.startswith(f"{self._at}/") for name in self._archive.namelist()
        )

    def exists(self) -> bool:
        """Return whether the path is a file or a folder in the archive."""
        return self.is_file() or self.is_dir()

    def iterdir(self) -> Iterator[ArchivePath]:
        """
        Yield the files and folders in this folder, in archive order (unspecified).

        Raises ValueError for a file or a missing folder, as `zipfile.Path` does.
        """
        if not self.is_dir():
            raise ValueError(f"Can't listdir a file: {self._at}")
        prefix = f"{self._at}/" if self._at else ""
        children = dict.fromkeys(
            name.removeprefix(prefix).partition("/")[0]
            for name in self._archive.namelist()
            if name.startswith(prefix) and name != prefix
        )
        return (self.joinpath(child) for child in children)

    @overload
    def open(
        self,
        mode: Literal["r"] = "r",
        *,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> IO[str]: ...

    @overload
    def open(self, mode: Literal["rb"]) -> IO[bytes]: ...

    def open(
        self,
        mode: str = "r",
        *,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> IO[Any]:
        """
        Open the file for reading, as text by default, as bytes with mode "rb".

        Raises FileNotFoundError for a missing file and IsADirectoryError for a
        folder, as `zipfile.Path` does.
        """
        if self.is_dir():
            raise IsADirectoryError(self._at)
        if not self.is_file():
            raise FileNotFoundError(self._at)
        stream = self._archive.open(self._at, mode="r")
        if "b" in mode:
            return stream
        return io.TextIOWrapper(stream, encoding=encoding, errors=errors)

    def read_bytes(self) -> bytes:
        """Return the content of the file."""
        with self.open("rb") as file:
            return file.read()

    def read_text(self, encoding: str | None = None, errors: str | None = None) -> str:
        """Return the content of the file as text."""
        with self.open(encoding=encoding, errors=errors) as file:
            return file.read()


@contextmanager
def extract(
    archive_path: Path, password: str | None = None
) -> Iterator[KNXProjContents]:
    """Provide the contents of a KNXProj file."""
    _LOGGER.debug('Opening KNX Project file "%s"', archive_path)
    try:
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
                # ZipPath is not supported by pyzipper thus KNXProjContents
                # uses an ArchivePath for the project folder
                yield KNXProjContents(
                    root_zip=zip_archive,
                    project_archive=project_zip,
                    project_relative_path="",
                    xml_namespace=xml_namespace,
                )
    except zlib.error as exception:
        # Decompression fails when the archive contents are damaged - eg. a broken
        # ETS export. ETS6 archives verify the password before decompression, so
        # this is not a wrong password there. ETS4/5 ZipCrypto only validates a
        # single check byte, so a wrong password does reach this about once in 256
        # attempts - but reporting every damaged file as "invalid password" would
        # send users down the wrong path far more often than the other way round.
        _LOGGER.error("Could not decompress project file: %s", exception)
        raise InvalidProjectArchive(
            "Could not decompress project data. The project file may be damaged."
            " Please try exporting it from ETS again."
        ) from exception
    except BadZipFile as exception:
        # The file is not a ZIP archive at all, is truncated, or a member fails its
        # CRC or - for password protected ETS6 projects - its authentication code.
        _LOGGER.error("Could not read project file: %s", exception)
        raise InvalidProjectArchive(
            "Could not read project data. The file may be damaged or not be an ETS"
            " project file. Please try exporting it from ETS again."
        ) from exception


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
