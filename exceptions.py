"""Custom exceptions."""


class MOSMapError(Exception):
    """Base exception for MOS workbook import failures."""


class SourceFileNotFoundError(MOSMapError):
    """Raised when a required source file is missing."""


class WorksheetStructureError(MOSMapError):
    """Raised when a worksheet's structure cannot be safely interpreted."""
