"""Tests for CreditEvaluator -- training stays separate from MOS equivalencies, source
lineage is preserved, duplicate courses are deduplicated, and totals are correct."""

from __future__ import annotations

from models import MOSCourseEquivalency, TrainingEquivalency
from services.credit_evaluator import CreditEvaluator


def _mos(course_id, credits, skill_level="10", mos_code="12P"):
    return MOSCourseEquivalency(
        mos_code, "Title", "Army", skill_level, course_id, "Title", credits, "AAS", "f", "s", "ok", ""
    )


def _training(training_id, course_id, credits, name="Training"):
    return TrainingEquivalency(
        training_id, "Army", name, "", course_id, credits, 5, False, "", "f", "t", "ok", ""
    )


def test_mos_and_training_credit_evaluated_independently_by_selection():
    mos_records = [_mos("CIS110", 3)]
    training_records = [_training("t1", "BUS137", 3)]
    evaluator = CreditEvaluator()

    mos_only = evaluator.build_credit_profile(mos_records, [("12P", "10")], training_records, [])
    assert {e.course_id for e in mos_only} == {"CIS110"}

    with_training = evaluator.build_credit_profile(mos_records, [("12P", "10")], training_records, ["t1"])
    assert {e.course_id for e in with_training} == {"CIS110", "BUS137"}


def test_source_lineage_preserved_in_profile_entries():
    mos_records = [_mos("CIS110", 3)]
    training_records = [_training("t1", "BUS137", 3, name="Advanced Leader Course")]
    profile = CreditEvaluator().build_credit_profile(mos_records, [("12P", "10")], training_records, ["t1"])
    by_course = {e.course_id: e.sources for e in profile}
    assert "12P" in by_course["CIS110"] and "10" in by_course["CIS110"]
    assert "Advanced Leader Course" in by_course["BUS137"]


def test_duplicate_course_from_multiple_sources_produces_one_entry():
    mos_records = [_mos("COM120", 3)]
    training_records = [_training("t1", "COM120", 3, name="Some Training")]
    profile = CreditEvaluator().build_credit_profile(mos_records, [("12P", "10")], training_records, ["t1"])
    matching = [e for e in profile if e.course_id == "COM120"]
    assert len(matching) == 1
    assert "12P" in matching[0].sources and "Some Training" in matching[0].sources


def test_duplicate_course_keeps_higher_credit_value_not_summed():
    mos_records = [_mos("COM120", 3)]
    training_records = [_training("t1", "COM120", 4, name="Some Training")]
    profile = CreditEvaluator().build_credit_profile(mos_records, [("12P", "10")], training_records, ["t1"])
    entry = next(e for e in profile if e.course_id == "COM120")
    assert entry.credits == 4  # higher of 3 and 4, never 3 + 4 = 7


def test_total_potential_credits_sums_distinct_courses_correctly():
    mos_records = [_mos("CIS110", 3), _mos("ELC112", 5)]
    profile = CreditEvaluator().build_credit_profile(mos_records, [("12P", "10")], [], [])
    assert sum(e.credits for e in profile) == 8


def test_zero_credit_records_excluded_from_profile():
    mos_records = [_mos("CIS110", 0)]
    profile = CreditEvaluator().build_credit_profile(mos_records, [("12P", "10")], [], [])
    assert profile == []


def test_different_mos_codes_at_different_skill_levels_merge_into_one_profile():
    mos_records = [
        _mos("CIS110", 3, skill_level="10", mos_code="12P"),
        _mos("ELC112", 4, skill_level="30", mos_code="25B"),
    ]
    profile = CreditEvaluator().build_credit_profile(
        mos_records, [("12P", "10"), ("25B", "30")], [], []
    )
    assert {e.course_id for e in profile} == {"CIS110", "ELC112"}
