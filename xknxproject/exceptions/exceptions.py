"""Exceptions for the project parser library."""


class XknxProjectException(Exception):
    """Library base exception class."""


class InvalidPasswordException(XknxProjectException):
    """Invalid password exception."""


class ProjectNotFoundException(XknxProjectException):
    """Project files not found in /tmp directory."""
