"""Entry point, orchestrates the pipeline."""

from __future__ import annotations

from pathlib import Path

from importers.mos_workbook_importer import MOSWorkbookImporter
from repositories.normalized_data_repository import write_csv

ROOT_DIR = Path(__file__).parent
SOURCE_DATA_DIR = ROOT_DIR / "source_data"
NORMALIZED_DATA_DIR = ROOT_DIR / "normalized_data"
CONVERSION_ISSUES_DIR = ROOT_DIR / "conversion_issues"


def main() -> None:
    importer = MOSWorkbookImporter()
    records, issues = importer.import_workbook(
        SOURCE_DATA_DIR / "Army_MOS_Maps_Reduced.xlsx"
    )

    write_csv(records, NORMALIZED_DATA_DIR / "mos_equivalencies.csv")
    write_csv(issues, CONVERSION_ISSUES_DIR / "mos_worksheet_issues.csv")

    worksheets_converted = len({(r.mos_code, r.source_sheet) for r in records})
    print("SOURCE CONVERSION SUMMARY")
    print(f"MOS worksheets converted:        {worksheets_converted}")
    print(f"MOS worksheets requiring review: {len(issues)}")
    print(f"MOS records written:             {len(records)}")
    for issue in issues:
        print(f"  - {issue.source_sheet}: {issue.message}")


if __name__ == "__main__":
    main()
