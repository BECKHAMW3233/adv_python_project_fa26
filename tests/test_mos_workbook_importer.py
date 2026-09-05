"""Tests for MOSWorkbookImporter -- sheet discovery, header detection, skill columns,
blank/zero handling, and malformed-sheet reporting."""

from __future__ import annotations

from importers.mos_workbook_importer import MOSWorkbookImporter
from tests.conftest import build_mos_workbook

_HEADER_ROW = (
    "Course ID",
    "Course Title",
    "Skill Level\n10",
    "Skill Level\n20",
    "Skill Level\n30",
    "Skill Level\n40",
    "Course Level",
)


def test_discovers_every_sheet_regardless_of_name(tmp_path):
    path = tmp_path / "mos.xlsx"
    build_mos_workbook(
        path,
        {
            "12P": [
                ("12P Prime Power Production Specialist",),
                (None, None, "Hours Earned"),
                _HEADER_ROW,
                ("CIS110", "Intro to Computers", 3, 3, 3, 3, "CAA"),
                ("64 Total Hours Required.",),
            ],
            "WeirdSheetName99": [
                ("25B Information Technology Specialist",),
                (None, None, "Hours Earned"),
                _HEADER_ROW,
                ("COM120", "Intro to Communication", 3, 3, 3, 3, "CAA"),
            ],
        },
    )
    records, issues = MOSWorkbookImporter().import_workbook(path)
    assert issues == []
    mos_codes = {r.mos_code for r in records}
    assert mos_codes == {"12P", "25B"}


def test_title_detected_with_and_without_leading_accessibility_row(tmp_path):
    path = tmp_path / "mos.xlsx"
    build_mos_workbook(
        path,
        {
            "WithAccessibilityRow": [
                ("Press UP or DOWN ARROW in column to read through the document.",),
                ("12P Prime Power Production Specialist",),
                (None, None, "Hours Earned"),
                _HEADER_ROW,
                ("CIS110", "Intro to Computers", 3, 3, 3, 3, "CAA"),
            ],
            "WithoutAccessibilityRow": [
                ("25B- Information Technology Specialist",),
                (None, None, "Hours Earned"),
                _HEADER_ROW,
                ("COM120", "Intro to Communication", 3, 3, 3, 3, "CAA"),
            ],
        },
    )
    records, issues = MOSWorkbookImporter().import_workbook(path)
    assert issues == []
    titles = {r.mos_code: r.mos_title for r in records}
    assert titles["12P"] == "Prime Power Production Specialist"
    assert titles["25B"] == "Information Technology Specialist"


def test_skill_level_columns_mapped_to_correct_skill_level(tmp_path):
    path = tmp_path / "mos.xlsx"
    build_mos_workbook(
        path,
        {
            "12P": [
                ("12P Prime Power Production Specialist",),
                (None, None, "Hours Earned"),
                _HEADER_ROW,
                ("CIS110", "Intro to Computers", 0, 0, 3, 4, "CAA"),
            ],
        },
    )
    records, _issues = MOSWorkbookImporter().import_workbook(path)
    by_level = {r.skill_level: r.credits for r in records}
    assert by_level == {"10": 0, "20": 0, "30": 3, "40": 4}


def test_blank_and_zero_skill_cells_both_mean_no_credit(tmp_path):
    path = tmp_path / "mos.xlsx"
    build_mos_workbook(
        path,
        {
            "25B": [
                ("25B Information Technology Specialist",),
                (None, None, "Hours Earned"),
                _HEADER_ROW,
                ("COM120", "Intro Interpersonal Communication", 0, None, 3, 3, "CAA"),
            ],
        },
    )
    records, _issues = MOSWorkbookImporter().import_workbook(path)
    by_level = {r.skill_level: r for r in records}
    assert by_level["10"].credits == 0 and by_level["10"].status == "no_credit"
    assert by_level["20"].credits == 0 and by_level["20"].status == "no_credit"
    assert by_level["30"].credits == 3 and by_level["30"].status == "ok"


def test_malformed_sheet_is_reported_not_crashed(tmp_path):
    path = tmp_path / "mos.xlsx"
    build_mos_workbook(
        path,
        {
            "Good": [
                ("12P Prime Power Production Specialist",),
                (None, None, "Hours Earned"),
                _HEADER_ROW,
                ("CIS110", "Intro to Computers", 3, 3, 3, 3, "CAA"),
            ],
            "Malformed": [
                ("Not a recognizable MOS title at all",),
                ("also not a header row",),
            ],
        },
    )
    records, issues = MOSWorkbookImporter().import_workbook(path)
    assert len(issues) == 1
    assert issues[0].source_sheet == "Malformed"
    assert {r.mos_code for r in records} == {"12P"}
