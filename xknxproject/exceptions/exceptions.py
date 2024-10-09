"""Exceptions for the project parser library."""


class XknxProjectException(Exception):
    """Library base exception class."""


class InvalidPasswordException(XknxProjectException):
    """Invalid password exception."""


class ProjectNotFoundException(XknxProjectException):
    """Project files not found in archive."""


class UnexpectedFileContent(XknxProjectException):
    """Unexpected file content."""


class UnexpectedDataError(XknxProjectException):
    """Unexpected data in project or application file."""
