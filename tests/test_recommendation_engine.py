"""Tests for RecommendationEngine -- requirement-type weights, applicable-credit capping
within a pick group, sorting by score, the full tie-break order, and the top-three limit."""

from __future__ import annotations

from models import CreditProfileEntry, ProgramRequirement
from services.recommendation_engine import RecommendationEngine


def _requirement(program_code, course_id, credits, requirement_type, choice_group_id="", target=None, program_title=None, total=60.0):
    return ProgramRequirement(
        program_code, program_title or program_code, "TRD", "2026", total, "Group",
        requirement_type, course_id, credits, choice_group_id, target, "f", 1, "raw", "ok", ""
    )


def test_weights_applied_correctly_to_ranking_points():
    profile = [CreditProfileEntry("ENG110", 3, "test")]
    records = [_requirement("A00001", "ENG110", 3, "general_education_choice")]
    rec = RecommendationEngine().recommend(profile, records)[0]
    assert rec.matched_courses[0].weight == 1
    assert rec.matched_courses[0].ranking_points == 3

    records2 = [_requirement("A00002", "ENG110", 3, "major_required")]
    rec2 = RecommendationEngine().recommend(profile, records2)[0]
    assert rec2.matched_courses[0].weight == 3
    assert rec2.matched_courses[0].ranking_points == 9


def test_applicable_credits_capped_within_a_pick_group_not_summed():
    profile = [CreditProfileEntry("MAT143", 3, "test"), CreditProfileEntry("MAT171", 4, "test")]
    records = [
        _requirement("A00001", "MAT143", 3, "general_education_choice", choice_group_id="A00001::Math Pick", target=3.0),
        _requirement("A00001", "MAT171", 4, "general_education_choice", choice_group_id="A00001::Math Pick", target=3.0),
    ]
    rec = RecommendationEngine().recommend(profile, records)[0]
    assert rec.applicable_matched_credits == 4  # highest-value course only, not 3 + 4 = 7
    assert len(rec.matched_courses) == 1
    assert len(rec.surplus_courses) == 1
    assert rec.surplus_courses[0].course_id == "MAT143"


def test_major_required_courses_never_capped_each_counts_independently():
    profile = [CreditProfileEntry("WLD110", 2, "test"), CreditProfileEntry("WLD115", 5, "test")]
    records = [
        _requirement("D00001", "WLD110", 2, "major_required"),
        _requirement("D00001", "WLD115", 5, "major_required"),
    ]
    rec = RecommendationEngine().recommend(profile, records)[0]
    assert rec.applicable_matched_credits == 7
    assert len(rec.matched_courses) == 2


def test_recommendations_sorted_by_score_descending():
    profile = [CreditProfileEntry("ENG110", 3, "test"), CreditProfileEntry("CIS110", 3, "test")]
    records = [
        _requirement("A00001", "ENG110", 3, "general_education_choice"),  # score 3
        _requirement("A00002", "ENG110", 3, "major_required"),  # score 9
        _requirement("A00002", "CIS110", 3, "major_required"),  # +9 = 18
    ]
    recs = RecommendationEngine().recommend(profile, records)
    assert [r.program_code for r in recs] == ["A00002", "A00001"]


def test_tie_break_prefers_more_major_required_credits_matched():
    profile = [CreditProfileEntry("ENG110", 3, "test"), CreditProfileEntry("CIS110", 3, "test")]
    records = [
        # Zeta: 1 major_required (9 pts) + 1 general_ed (3 pts) = score 12, major_required credits = 3
        _requirement("Z0001", "ENG110", 3, "major_required", program_title="Zeta Program"),
        _requirement("Z0001", "CIS110", 3, "general_education_choice", program_title="Zeta Program"),
        # Alpha: 2 major_choice (6+6=12 pts) = score 12, major_required credits = 0
        _requirement("A0001", "ENG110", 3, "major_choice", program_title="Alpha Program"),
        _requirement("A0001", "CIS110", 3, "major_choice", program_title="Alpha Program"),
    ]
    recs = RecommendationEngine().recommend(profile, records)
    assert recs[0].recommendation_score == recs[1].recommendation_score == 12
    assert recs[0].program_code == "Z0001"  # wins tie-break despite being alphabetically after Alpha


def test_programs_with_no_exact_match_are_excluded_not_just_deprioritized():
    profile = [CreditProfileEntry("ENG110", 3, "test")]
    records = [_requirement("A00001", "CIS110", 3, "major_required")]  # no overlap with profile
    recs = RecommendationEngine().recommend(profile, records)
    assert recs == []


def test_top_three_limit_enforced_even_with_more_matches():
    profile = [CreditProfileEntry("ENG110", 3, "test")]
    records = [
        _requirement(f"P0000{i}", "ENG110", 3, "major_required", program_title=f"Program {i}")
        for i in range(5)
    ]
    recs = RecommendationEngine().recommend(profile, records)
    assert len(recs) == 3
