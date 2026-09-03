"""Custom exceptions."""


class SourceConversionError(Exception):
    """Base exception for source-file import/conversion failures."""


class SourceFileNotFoundError(SourceConversionError):
    """Raised when a required source file is missing."""


class WorksheetStructureError(SourceConversionError):
    """Raised when a worksheet's structure cannot be safely interpreted."""
