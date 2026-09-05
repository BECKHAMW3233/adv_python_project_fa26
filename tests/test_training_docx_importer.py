"""Tests for TrainingDocxImporter -- branch detection, multi-course cells, separators,
narrative exclusion, and ambiguous (combined) hours handling."""

from __future__ import annotations

from importers.training_docx_importer import TrainingDocxImporter
from tests.conftest import build_training_docx

_HEADER = ["Course Name", "FTCC Equivalency", "Hours"]


def test_branch_heading_detected_and_applied_to_following_rows(tmp_path):
    path = tmp_path / "training.docx"
    build_training_docx(
        path,
        [
            [
                ["ARMY", "ARMY", "ARMY"],
                _HEADER,
                ["Some Training", "CIS 110", "3"],
            ]
        ],
    )
    records, issues = TrainingDocxImporter().import_document(path)
    assert issues == []
    assert all(r.branch == "ARMY" for r in records)


def test_multiple_courses_in_one_cell_expand_to_multiple_records(tmp_path):
    path = tmp_path / "training.docx"
    build_training_docx(
        path,
        [
            [
                ["ARMY", "ARMY", "ARMY"],
                _HEADER,
                ["Advanced Leader Course", "BUS 137, BUS 234", "6"],
            ]
        ],
    )
    records, _issues = TrainingDocxImporter().import_document(path)
    course_ids = {r.course_id for r in records}
    assert course_ids == {"BUS137", "BUS234"}


def test_ampersand_separator_also_splits_equivalencies(tmp_path):
    path = tmp_path / "training.docx"
    build_training_docx(
        path,
        [
            [
                ["COAST GUARD", "COAST GUARD", "COAST GUARD"],
                _HEADER,
                ["Master Chief Petty Officer", "BUS153 & OMT 156", "6"],
            ]
        ],
    )
    records, _issues = TrainingDocxImporter().import_document(path)
    course_ids = {r.course_id for r in records}
    assert course_ids == {"BUS153", "OMT156"}


def test_narrative_paragraphs_outside_tables_are_ignored(tmp_path):
    path = tmp_path / "training.docx"
    build_training_docx(
        path,
        [
            [
                ["ARMY", "ARMY", "ARMY"],
                _HEADER,
                ["Some Training", "CIS 110", "3"],
            ]
        ],
        narrative="MEMORANDUM\nTO: Academic Leadership\nThis is not a table and must be ignored.",
    )
    records, _issues = TrainingDocxImporter().import_document(path)
    assert len(records) == 1
    assert records[0].course_id == "CIS110"


def test_ambiguous_combined_hours_left_unresolved_not_invented(tmp_path):
    path = tmp_path / "training.docx"
    build_training_docx(
        path,
        [
            [
                ["ARMY", "ARMY", "ARMY"],
                _HEADER,
                ["SOCM Course", "BIO 163, HSC 120, MED 120", "9"],
            ]
        ],
    )
    records, _issues = TrainingDocxImporter().import_document(path)
    assert len(records) == 3
    for record in records:
        assert record.course_credits is None
        assert record.verification_required is True
        assert record.status == "credits_unresolved"
        assert record.source_total_hours == 9
