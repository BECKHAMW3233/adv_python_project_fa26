"""Custom exceptions."""


class SourceConversionError(Exception):
    """Base exception for source-file import/conversion failures."""


class SourceFileNotFoundError(SourceConversionError):
    """Raised when a required source file is missing."""


class WorksheetStructureError(SourceConversionError):
    """Raised when a worksheet's structure cannot be safely interpreted."""


class InvalidSelectionError(Exception):
    """Raised when a user's menu/selection input doesn't correspond to a valid choice."""
