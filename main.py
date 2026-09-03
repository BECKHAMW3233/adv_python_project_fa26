"""Entry point, orchestrates the pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from exceptions import SourceConversionError
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


def _needs_conversion(force_refresh: bool) -> tuple[bool, str]:
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


def _convert() -> tuple[list, list, list, list, list, list]:
    mos_importer = MOSWorkbookImporter()
    mos_records, mos_issues = mos_importer.import_workbook(MOS_SOURCE)
    write_csv(mos_records, MOS_CSV)
    write_csv(mos_issues, CONVERSION_ISSUES_DIR / "mos_worksheet_issues.csv")

    training_importer = TrainingDocxImporter()
    training_records, training_issues = training_importer.import_document(TRAINING_SOURCE)
    write_csv(training_records, TRAINING_CSV)
    write_csv(training_issues, CONVERSION_ISSUES_DIR / "training_table_issues.csv")

    program_importer = ProgramWorkbookImporter()
    program_records, program_issues = program_importer.import_workbook(PROGRAM_SOURCE)
    write_csv(program_records, PROGRAM_CSV)
    write_csv(program_issues, CONVERSION_ISSUES_DIR / "program_workbook_issues.csv")

    write_manifest(MANIFEST_PATH, {path.name: compute_file_hash(path) for path in SOURCE_FILES})

    return (
        mos_records,
        mos_issues,
        training_records,
        training_issues,
        program_records,
        program_issues,
    )


def _load() -> tuple[list, list, list, list, list, list]:
    mos_records = read_csv(MOSCourseEquivalency, MOS_CSV)
    training_records = read_csv(TrainingEquivalency, TRAINING_CSV)
    program_records = read_csv(ProgramRequirement, PROGRAM_CSV)
    return mos_records, [], training_records, [], program_records, []


def _print_summary(
    mos_records: list,
    mos_issues: list,
    training_records: list,
    training_issues: list,
    program_records: list,
    program_issues: list,
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


def main() -> None:
    parser = argparse.ArgumentParser(description="FTCC Military Credit and Program Recommender")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force reconversion of source files even if normalized data looks current.",
    )
    args = parser.parse_args()

    needs_conversion, reason = _needs_conversion(args.refresh)

    if needs_conversion:
        print(f"Converting source files ({reason})...")
        try:
            records = _convert()
        except SourceConversionError as exc:
            print(f"ERROR: source conversion failed -- {exc}")
            CONVERSION_ISSUES_DIR.mkdir(parents=True, exist_ok=True)
            (CONVERSION_ISSUES_DIR / "fatal_conversion_error.txt").write_text(
                f"{type(exc).__name__}: {exc}\n", encoding="utf-8"
            )
            sys.exit(1)
        _print_summary(*records)
    else:
        print("Normalized data is current -- loading existing files without reconversion.")
        mos_records, _, training_records, _, program_records, _ = _load()
        print(
            f"Loaded {len(mos_records)} MOS records, {len(training_records)} training records, "
            f"{len(program_records)} program requirement records."
        )
        print("Run with --refresh to force reconversion from source files.")


if __name__ == "__main__":
    main()
