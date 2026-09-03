"""Entry point, orchestrates the pipeline."""

from __future__ import annotations

from pathlib import Path

from importers.mos_workbook_importer import MOSWorkbookImporter
from importers.program_workbook_importer import ProgramWorkbookImporter
from importers.training_docx_importer import TrainingDocxImporter
from repositories.normalized_data_repository import write_csv

ROOT_DIR = Path(__file__).parent
SOURCE_DATA_DIR = ROOT_DIR / "source_data"
NORMALIZED_DATA_DIR = ROOT_DIR / "normalized_data"
CONVERSION_ISSUES_DIR = ROOT_DIR / "conversion_issues"


def main() -> None:
    mos_importer = MOSWorkbookImporter()
    mos_records, mos_issues = mos_importer.import_workbook(
        SOURCE_DATA_DIR / "Army_MOS_Maps_Reduced.xlsx"
    )
    write_csv(mos_records, NORMALIZED_DATA_DIR / "mos_equivalencies.csv")
    write_csv(mos_issues, CONVERSION_ISSUES_DIR / "mos_worksheet_issues.csv")

    training_importer = TrainingDocxImporter()
    training_records, training_issues = training_importer.import_document(
        SOURCE_DATA_DIR / "Appendix J for website2026 (002).docx"
    )
    write_csv(training_records, NORMALIZED_DATA_DIR / "training_equivalencies.csv")
    write_csv(training_issues, CONVERSION_ISSUES_DIR / "training_table_issues.csv")

    program_importer = ProgramWorkbookImporter()
    program_records, program_issues = program_importer.import_workbook(
        SOURCE_DATA_DIR / "2026_POS_Reduced.xlsx"
    )
    write_csv(program_records, NORMALIZED_DATA_DIR / "program_requirements.csv")
    write_csv(program_issues, CONVERSION_ISSUES_DIR / "program_workbook_issues.csv")

    worksheets_converted = len({(r.mos_code, r.source_sheet) for r in mos_records})
    print("SOURCE CONVERSION SUMMARY")
    print(f"MOS worksheets converted:        {worksheets_converted}")
    print(f"MOS worksheets requiring review: {len(mos_issues)}")
    print(f"MOS records written:             {len(mos_records)}")
    for issue in mos_issues:
        print(f"  - {issue.source_sheet}: {issue.message}")
    print()
    training_rows_converted = len(
        {(r.branch, r.training_name) for r in training_records}
    )
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


if __name__ == "__main__":
    main()
