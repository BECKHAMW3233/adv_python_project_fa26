"""Pipeline orchestration -- first-run/refresh detection, source conversion, loading
existing normalized data, and validation. Split out of main.py so that entry-point/CLI
concerns and pipeline concerns aren't mixed in one file."""

from __future__ import annotations

import logging
from pathlib import Path

from importers.mos_workbook_importer import MOSWorkbookImporter
from importers.program_workbook_importer import ProgramWorkbookImporter
from importers.training_docx_importer import TrainingDocxImporter
from models import MOSCourseEquivalency, ProgramRequirement, TrainingEquivalency
from repositories.normalized_data_repository import (
    compute_file_hash,
    read_csv,
    read_manifest,
    write_csv,
    write_manifest,
)
from services.conversion_validator import ConversionValidator

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
SOURCE_DATA_DIR = ROOT_DIR / "source_data"
NORMALIZED_DATA_DIR = ROOT_DIR / "normalized_data"
CONVERSION_ISSUES_DIR = ROOT_DIR / "conversion_issues"

MOS_SOURCE = SOURCE_DATA_DIR / "Army_MOS_Maps_Reduced.xlsx"
TRAINING_SOURCE = SOURCE_DATA_DIR / "Appendix J for website2026 (002).docx"
PROGRAM_SOURCE = SOURCE_DATA_DIR / "2026_POS_Reduced.xlsx"
SOURCE_FILES = (MOS_SOURCE, TRAINING_SOURCE, PROGRAM_SOURCE)

MOS_CSV = NORMALIZED_DATA_DIR / "mos_equivalencies.csv"
TRAINING_CSV = NORMALIZED_DATA_DIR / "training_equivalencies.csv"
PROGRAM_CSV = NORMALIZED_DATA_DIR / "program_requirements.csv"
NORMALIZED_FILES = (MOS_CSV, TRAINING_CSV, PROGRAM_CSV)

MANIFEST_PATH = NORMALIZED_DATA_DIR / ".conversion_manifest.json"


def needs_conversion(force_refresh: bool) -> tuple[bool, str]:
    if force_refresh:
        return True, "refresh requested (--refresh)"
    if not all(path.exists() for path in NORMALIZED_FILES):
        return True, "normalized output missing"
    manifest = read_manifest(MANIFEST_PATH)
    current_hashes = {path.name: compute_file_hash(path) for path in SOURCE_FILES}
    if current_hashes != manifest:
        changed = sorted(
            name for name in current_hashes if manifest.get(name) != current_hashes[name]
        )
        return True, f"source file(s) changed: {', '.join(changed)}"
    return False, ""


def convert() -> tuple[list, list, list, list, list, list]:
    mos_importer = MOSWorkbookImporter()
    mos_records, mos_issues = mos_importer.import_workbook(MOS_SOURCE)
    write_csv(mos_records, MOS_CSV)
    write_csv(mos_issues, CONVERSION_ISSUES_DIR / "mos_worksheet_issues.csv")
    logger.info(
        "MOS conversion: %d records, %d worksheet issues", len(mos_records), len(mos_issues)
    )
    for issue in mos_issues:
        logger.warning("MOS worksheet issue [%s]: %s", issue.source_sheet, issue.message)

    training_importer = TrainingDocxImporter()
    training_records, training_issues = training_importer.import_document(TRAINING_SOURCE)
    write_csv(training_records, TRAINING_CSV)
    write_csv(training_issues, CONVERSION_ISSUES_DIR / "training_table_issues.csv")
    logger.info(
        "Training conversion: %d records, %d table issues",
        len(training_records),
        len(training_issues),
    )
    for issue in training_issues:
        logger.warning("Training table issue [%s]: %s", issue.source_table, issue.message)

    program_importer = ProgramWorkbookImporter()
    program_records, program_issues = program_importer.import_workbook(PROGRAM_SOURCE)
    write_csv(program_records, PROGRAM_CSV)
    write_csv(program_issues, CONVERSION_ISSUES_DIR / "program_workbook_issues.csv")
    logger.info(
        "Program conversion: %d records, %d workbook issues",
        len(program_records),
        len(program_issues),
    )
    for issue in program_issues:
        logger.warning("Program workbook issue [row %d]: %s", issue.source_row, issue.message)

    write_manifest(MANIFEST_PATH, {path.name: compute_file_hash(path) for path in SOURCE_FILES})
    logger.info("Conversion manifest written")

    return (
        mos_records,
        mos_issues,
        training_records,
        training_issues,
        program_records,
        program_issues,
    )


def load() -> tuple[list, list, list, list, list, list]:
    mos_records = read_csv(MOSCourseEquivalency, MOS_CSV)
    training_records = read_csv(TrainingEquivalency, TRAINING_CSV)
    program_records = read_csv(ProgramRequirement, PROGRAM_CSV)
    logger.info(
        "Loaded existing normalized data: %d MOS, %d training, %d program records",
        len(mos_records),
        len(training_records),
        len(program_records),
    )
    return mos_records, [], training_records, [], program_records, []


def validate_and_report(mos_records: list, training_records: list, program_records: list) -> list:
    issues = ConversionValidator().validate(mos_records, training_records, program_records)
    write_csv(issues, CONVERSION_ISSUES_DIR / "validation_issues.csv")
    warnings = sum(1 for i in issues if i.severity == "warning")
    errors = sum(1 for i in issues if i.severity == "error")
    logger.info("Validation complete: %d warning(s), %d error(s)", warnings, errors)
    for issue in issues:
        log_fn = logger.error if issue.severity == "error" else logger.warning
        log_fn("Validation %s [%s/%s]: %s", issue.severity, issue.source, issue.identifier, issue.message)
    return issues


def print_summary(
    mos_records: list,
    mos_issues: list,
    training_records: list,
    training_issues: list,
    program_records: list,
    program_issues: list,
    validation_issues: list,
) -> None:
    worksheets_converted = len({(r.mos_code, r.source_sheet) for r in mos_records})
    print("SOURCE CONVERSION SUMMARY")
    print(f"MOS worksheets converted:        {worksheets_converted}")
    print(f"MOS worksheets requiring review: {len(mos_issues)}")
    print(f"MOS records written:             {len(mos_records)}")
    for issue in mos_issues:
        print(f"  - {issue.source_sheet}: {issue.message}")
    print()
    training_rows_converted = len({(r.branch, r.training_name) for r in training_records})
    print(f"Training rows converted:           {training_rows_converted}")
    print(f"Training tables requiring review:  {len(training_issues)}")
    print(f"Training records written:          {len(training_records)}")
    for issue in training_issues:
        print(f"  - {issue.source_table}: {issue.message}")
    print()
    programs_converted = len({r.program_code for r in program_records})
    print(f"Program records converted:         {programs_converted}")
    print(f"Program workbook issues:           {len(program_issues)}")
    print(f"Program requirement records:       {len(program_records)}")
    for issue in program_issues:
        print(f"  - row {issue.source_row}: {issue.message}")
    print()
    warnings = [i for i in validation_issues if i.severity == "warning"]
    errors = [i for i in validation_issues if i.severity == "error"]
    print(f"Warnings:                         {len(warnings)}")
    print(f"Errors:                           {len(errors)}")
    for issue in validation_issues:
        print(f"  - [{issue.severity}] {issue.source}/{issue.identifier}: {issue.message}")
