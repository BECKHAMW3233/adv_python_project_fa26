"""Custom exceptions."""


class SourceConversionError(Exception):
    """Base exception for source-file import/conversion failures."""


class SourceFileNotFoundError(SourceConversionError):
    """Raised when a required source file is missing."""


class WorksheetStructureError(SourceConversionError):
    """Raised when a worksheet's structure cannot be safely interpreted."""


class DocxParsingError(SourceConversionError):
    """Raised when the training Word document's structure cannot be safely interpreted."""


class MissingProgramTotalError(SourceConversionError):
    """Raised when a program's total credits cannot be determined from the source; caught
    per-program by the importer and turned into a ProgramWorkbookIssue rather than failing
    the whole conversion."""


class InvalidSelectionError(Exception):
    """Raised when a user's menu/selection input doesn't correspond to a valid choice."""


class ReportExportError(Exception):
    """Raised when a recommendation report fails to write to disk."""


class UserExitRequested(Exception):
    """Raised when the user types 'exit' at any interactive prompt; caught once at the top
    of main() to end the program immediately, without generating a report."""


class UserBackRequested(Exception):
    """Raised when the user types 'back' at any interactive prompt; caught by the nearest
    enclosing loop to retry the step (or phase) that came before the current one."""
