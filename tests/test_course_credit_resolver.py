"""Tests for CourseCreditResolver -- building a course_id -> credits reference from the
program catalog and already-resolved training rows, and using it (never arithmetic) to
resolve previously-ambiguous training rows."""

from __future__ import annotations

from models import ProgramRequirement, TrainingEquivalency
from services.course_credit_resolver import build_reference, resolve_training_credits


def _program(course_id: str, credits: int, program_code: str = "A00001") -> ProgramRequirement:
    return ProgramRequirement(
        program_code, program_code, "TRD", "2026", 60.0, "Group", "major_required",
        course_id, credits, "", None, "f", 1, "raw", "ok", ""
    )


def _training(
    training_id: str,
    course_id: str,
    credits: int | None,
    status: str,
    training_name: str = "Some Training",
    hours: int | None = None,
) -> TrainingEquivalency:
    return TrainingEquivalency(
        training_id, "ARMY", training_name, "", course_id, credits, hours,
        status != "ok", "", "f", "table_0", status,
        "" if status == "ok" else "Combined hours cover multiple courses; per-course credit not invented, see source_total_hours",
    )


def test_reference_prefers_program_catalog_over_training_row():
    programs = [_program("HUM230", 3)]
    trainings = [_training("T1", "HUM230", 5, "ok", "Some Other Training")]
    reference = build_reference(programs, trainings)
    assert reference["HUM230"].credits == 3
    assert reference["HUM230"].source == "program_catalog"


def test_reference_falls_back_to_resolved_training_row_when_not_in_catalog():
    programs = [_program("CIS110", 3)]  # unrelated course, doesn't mention BUS234
    trainings = [_training("T1", "BUS234", 3, "ok", "SHARP certification")]
    reference = build_reference(programs, trainings)
    assert "BUS234" in reference
    assert reference["BUS234"].credits == 3
    assert reference["BUS234"].source == "training:SHARP certification"


def test_reference_excludes_courses_with_no_confirmed_value_anywhere():
    programs = [_program("CIS110", 3)]
    trainings = [_training("T1", "PED172", None, "credits_unresolved", hours=7)]
    reference = build_reference(programs, trainings)
    assert "PED172" not in reference


def test_resolve_fills_in_unresolved_rows_found_in_reference():
    reference = build_reference([_program("HUM230", 3)], [])
    unresolved = [_training("BLC", "HUM230", None, "credits_unresolved", "Army Basic Leader Course (BLC)", hours=6)]
    resolved = resolve_training_credits(unresolved, reference)
    assert resolved[0].course_credits == 3
    assert resolved[0].status == "ok"
    assert resolved[0].verification_required is False
    assert "course-credit reference" in resolved[0].notes
    assert "6 hours" in resolved[0].notes


def test_resolve_leaves_unmatched_rows_untouched():
    reference = build_reference([_program("HUM230", 3)], [])
    unresolved = [_training("ABT", "PED172", None, "credits_unresolved", "Army Basic Training", hours=7)]
    resolved = resolve_training_credits(unresolved, reference)
    assert resolved[0] == unresolved[0]
    assert resolved[0].status == "credits_unresolved"


def test_resolve_does_not_touch_already_ok_rows():
    reference = build_reference([_program("HUM230", 99)], [])  # deliberately different value
    already_ok = [_training("T1", "HUM230", 3, "ok", "Master Fitness", hours=3)]
    resolved = resolve_training_credits(already_ok, reference)
    assert resolved[0].course_credits == 3  # unchanged, not overwritten by the reference
