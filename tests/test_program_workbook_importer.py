"""Tests for ProgramWorkbookImporter -- program boundaries, repeated page headers, course
extraction (both structured and flattened-text rows), choice groups, and unsupported
(nested) rules."""

from __future__ import annotations

from importers.program_workbook_importer import ProgramWorkbookImporter
from tests.conftest import build_program_workbook


def _header(code: str, title: str) -> dict[int, object]:
    return {0: f"Program of Study: {title} ({code}) Type: TRD Catalog: 2026 Catalog Year"}


def _structured_course(label: str, term: str, title: str, class_hr: int, lab_hr: int, credits: int) -> dict[int, object]:
    return {0: label, 22: term, 25: title, 55: class_hr, 56: lab_hr, 57: 0, 59: credits}


def _footer_total(total: int) -> dict[int, object]:
    """A program's total-credits footer: a lone negative int (Excel's accounting format
    renders negatives in parentheses, so the raw value is the total, sign-flipped)."""
    return {59: -total}


def test_program_boundaries_separate_distinct_programs(tmp_path):
    path = tmp_path / "programs.xlsx"
    rows = [
        _header("A11111", "Test Program One"),
        {0: "1) General Education Requirements GE Required Courses > Take 3 credits"},
        _structured_course("From S00001  ENG-110", "2025FA", "Freshman Comp", 3, 0, 3),
        _footer_total(66),
        _header("A22222", "Test Program Two"),
        {0: "1) General Education Requirements GE Required Courses > Take 3 credits"},
        _structured_course("From S00002  MAT-110", "2025FA", "Basic Math", 3, 0, 3),
        _footer_total(66),
    ]
    build_program_workbook(path, rows)
    records, issues = ProgramWorkbookImporter().import_workbook(path)
    assert issues == []
    by_program = {r.program_code: r.course_id for r in records}
    assert by_program == {"A11111": "ENG110", "A22222": "MAT110"}


def test_repeated_page_header_does_not_reset_program_or_lose_total(tmp_path):
    path = tmp_path / "programs.xlsx"
    rows = [
        _header("A11111", "Test Program"),
        {0: "1) General Education Requirements GE Required Courses > Take 3 credits"},
        _structured_course("From S00001  ENG-110", "2025FA", "Freshman Comp", 3, 0, 3),
        {0: "Program of Study: Test Program (A11111) Type: TRD Catalog: 2026 Catalog Year (66.00)"},
        _structured_course("S00002  MAT-110", "2025FA", "Basic Math", 3, 0, 3),
    ]
    build_program_workbook(path, rows)
    records, _issues = ProgramWorkbookImporter().import_workbook(path)
    assert {r.program_code for r in records} == {"A11111"}
    assert {r.course_id for r in records} == {"ENG110", "MAT110"}
    assert all(r.program_total_credits == 66.0 for r in records)


def test_course_extraction_structured_and_flattened_text(tmp_path):
    path = tmp_path / "programs.xlsx"
    rows = [
        _header("A11111", "Test Program"),
        {0: "2) Major Requirements MAJ Required Courses > Take 6 credits"},
        _structured_course("From S00001  CIS-110", "2025FA", "Intro Computers", 3, 0, 3),
        {
            0: "S00002  CTI-110   2025FA  IT Foundations                    "
            "2.00    2.00    0.00        3.00"
        },
        _footer_total(66),
    ]
    build_program_workbook(path, rows)
    records, issues = ProgramWorkbookImporter().import_workbook(path)
    assert issues == []
    by_course = {r.course_id: r.course_credits for r in records}
    assert by_course == {"CIS110": 3, "CTI110": 3}


def test_choice_group_id_and_target_shared_across_options(tmp_path):
    path = tmp_path / "programs.xlsx"
    rows = [
        _header("A11111", "Test Program"),
        {0: "2) Major Requirements MAJ Required Pick > Take 3 credits"},
        _structured_course("From S00001  CIS-110", "2025FA", "Intro Computers", 3, 0, 3),
        _structured_course("S00002  NOS-110", "2025FA", "OS Concepts", 3, 0, 3),
    ]
    build_program_workbook(path, rows)
    records, _issues = ProgramWorkbookImporter().import_workbook(path)
    assert len(records) == 2
    group_ids = {r.choice_group_id for r in records}
    targets = {r.choice_group_target_credits for r in records}
    types = {r.requirement_type for r in records}
    assert len(group_ids) == 1 and next(iter(group_ids))
    assert targets == {3.0}
    assert types == {"major_choice"}


def test_take_instruction_on_a_later_row_than_its_subgroup_label(tmp_path):
    """Regression test: a real row pattern splits a subgroup's label onto one row and its
    "> Take N credits" (plus the first course) onto the next -- discovered via a validator
    check that found 659 real program records missing their pick-group target credits."""
    path = tmp_path / "programs.xlsx"
    rows = [
        _header("A11111", "Test Program"),
        {0: "1) General Education Requirements"},
        {0: "HUM/FINE Arts Pick"},
        {**_structured_course("> Take", "2025FA", "Art Appreciation", 3, 0, 3), 8: "3 credits\nFrom S00001  ART-111"},
        _structured_course("S00002  HUM-110", "2025FA", "Tech and Society", 3, 0, 3),
        _footer_total(66),
    ]
    build_program_workbook(path, rows)
    records, issues = ProgramWorkbookImporter().import_workbook(path)
    assert issues == []
    targets = {r.choice_group_target_credits for r in records}
    assert targets == {3.0}


def test_take_instruction_with_a_stray_number_before_the_real_credit_count(tmp_path):
    """Regression test: some Pick groups read like "> Take 2 8 credits" (an extra number,
    likely a course-count, sitting before the real credit total) -- the last number
    immediately before "credits" is always the one that counts."""
    path = tmp_path / "programs.xlsx"
    rows = [
        _header("A11111", "Test Program"),
        {0: "Maj Other Required Pick > Take 2 8 credits From S00001  BAS-120"},
        _structured_course("S00002  BAS-121", "2025FA", "X", 3, 0, 3),
        _footer_total(66),
    ]
    build_program_workbook(path, rows)
    records, issues = ProgramWorkbookImporter().import_workbook(path)
    assert issues == []
    assert all(r.choice_group_target_credits == 8.0 for r in records)


def test_unsupported_nested_rule_flagged_manual_review_not_guessed(tmp_path):
    path = tmp_path / "programs.xlsx"
    rows = [
        _header("A11111", "Test Program"),
        {0: "2) Major Requirements MAJ Other Required Pick > Take 1 of 2 Groups"},
        _structured_course("From S00001  MED-120", "2025FA", "Med Terminology", 3, 0, 3),
    ]
    build_program_workbook(path, rows)
    records, _issues = ProgramWorkbookImporter().import_workbook(path)
    assert len(records) == 1
    assert records[0].status == "manual_review"
