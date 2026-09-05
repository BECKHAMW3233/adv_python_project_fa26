"""Tests for ConversionValidator -- missing fields, duplicate keys, unresolved credits,
and that issues are reported at the correct severity."""

from __future__ import annotations

from models import MOSCourseEquivalency, ProgramRequirement, TrainingEquivalency
from services.conversion_validator import ConversionValidator


def _mos(mos_code="12P", skill_level="10", course_id="CIS110", credits=3, status="ok"):
    return MOSCourseEquivalency(
        mos_code, "Title", "Army", skill_level, course_id, "Title", credits, "AAS", "f", "s", status, ""
    )


def _training(course_id="", course_credits=3, status="ok"):
    return TrainingEquivalency(
        "id1", "Army", "Name", "", course_id, course_credits, 5, True, "", "f", "t", status, ""
    )


def _program(
    program_code="A11111",
    program_title="Program",
    course_id="CIS110",
    credits=3,
    requirement_type="major_required",
    status="ok",
    choice_group_target_credits=3.0,
    program_total_credits=66.0,
):
    return ProgramRequirement(
        program_code, program_title, "TRD", "2026", program_total_credits, "Major",
        requirement_type, course_id, credits, "grp", choice_group_target_credits,
        "f", 1, "raw", status, ""
    )


def test_missing_required_field_is_an_error():
    issues = ConversionValidator().validate([_mos(mos_code="")], [], [])
    assert len(issues) == 1
    assert issues[0].severity == "error"


def test_duplicate_mos_skill_course_combination_is_an_error():
    issues = ConversionValidator().validate([_mos(), _mos()], [], [])
    assert any("Duplicated" in i.message for i in issues)
    assert all(i.severity == "error" for i in issues if "Duplicated" in i.message)


def test_unresolved_training_credits_excused_by_status_is_not_flagged():
    issues = ConversionValidator().validate(
        [], [_training(course_id="", status="no_equivalency_found")], []
    )
    assert issues == []


def test_unresolved_training_credits_without_excuse_is_a_warning():
    issues = ConversionValidator().validate([], [_training(course_id="", status="ok")], [])
    assert len(issues) == 1
    assert issues[0].severity == "warning"


def test_bad_course_id_format_is_an_error():
    issues = ConversionValidator().validate([_mos(course_id="cis 110")], [], [])
    assert any(i.severity == "error" and "format" in i.message for i in issues)


def test_program_with_no_known_title_is_an_error():
    issues = ConversionValidator().validate([], [], [_program(program_title="")])
    assert any(i.severity == "error" and "no known title" in i.message for i in issues)


def test_choice_type_without_target_credits_is_an_error():
    issues = ConversionValidator().validate(
        [], [], [_program(requirement_type="major_choice", choice_group_target_credits=None)]
    )
    assert any(i.severity == "error" and "pick-group credit cap" in i.message for i in issues)


def test_major_required_without_target_credits_is_not_flagged():
    issues = ConversionValidator().validate(
        [], [], [_program(requirement_type="major_required", choice_group_target_credits=None)]
    )
    assert issues == []


def test_missing_program_total_is_a_warning_reported_once_per_program():
    records = [
        _program(course_id="CIS110", program_total_credits=None),
        _program(course_id="ENG110", program_total_credits=None),
    ]
    issues = ConversionValidator().validate([], [], records)
    total_warnings = [i for i in issues if "no detected total credits" in i.message]
    assert len(total_warnings) == 1
    assert total_warnings[0].severity == "warning"


def test_clean_records_produce_no_issues():
    issues = ConversionValidator().validate([_mos()], [_training(course_id="CIS110")], [_program()])
    assert issues == []
