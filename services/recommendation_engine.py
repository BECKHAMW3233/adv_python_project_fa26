"""RecommendationEngine -- match, score, rank, tie-break, and explain."""

from __future__ import annotations

from typing import Sequence

from config import RECOMMENDATION_WEIGHTS
from models import CreditProfileEntry, MatchedCourse, ProgramRecommendation, ProgramRequirement

_REQUIREMENT_TYPE_LABELS = {
    "major_required": "a required major course",
    "major_choice": "an elective choice within a major requirement group",
    "general_education_choice": "a choice within a general education requirement group",
}


class RecommendationEngine:
    """Matches a veteran's potential-credit profile against FTCC programs, scores and ranks them."""

    def recommend(
        self,
        profile: Sequence[CreditProfileEntry],
        program_records: Sequence[ProgramRequirement],
        top_n: int = 3,
    ) -> list[ProgramRecommendation]:
        profile_credits = {entry.course_id: entry.credits for entry in profile}

        by_program: dict[str, list[ProgramRequirement]] = {}
        for record in program_records:
            by_program.setdefault(record.program_code, []).append(record)

        recommendations = [
            recommendation
            for records in by_program.values()
            if (recommendation := self._score_program(profile_credits, records)) is not None
        ]

        recommendations.sort(
            key=lambda r: (
                -r.recommendation_score,
                -r.major_required_credits_matched,
                -r.applicable_matched_credits,
                -len(r.matched_courses),
                -(r.match_percentage or 0),
                r.program_title,
            )
        )
        return recommendations[:top_n]

    def _score_program(
        self, profile_credits: dict[str, int], records: Sequence[ProgramRequirement]
    ) -> ProgramRecommendation | None:
        # A course can appear under more than one requirement group in the same program
        # (e.g. both a direct major requirement and, elsewhere, an elective choice); when
        # that happens, the higher-weighted classification is the one actually usable, so
        # keep the best match per course rather than the first one encountered.
        best_match: dict[str, ProgramRequirement] = {}
        for record in records:
            if record.course_id not in profile_credits:
                continue
            weight = RECOMMENDATION_WEIGHTS.get(record.requirement_type)
            if weight is None:
                continue  # unresolved/unclassified requirement type -- do not guess, do not score
            existing = best_match.get(record.course_id)
            if existing is None or weight > RECOMMENDATION_WEIGHTS[existing.requirement_type]:
                best_match[record.course_id] = record

        if not best_match:
            return None  # programs with no exact matches are not ranked at all

        matched_courses = [
            MatchedCourse(
                course_id=record.course_id,
                credits=profile_credits[record.course_id],
                requirement_type=record.requirement_type,
                weight=RECOMMENDATION_WEIGHTS[record.requirement_type],
                ranking_points=profile_credits[record.course_id]
                * RECOMMENDATION_WEIGHTS[record.requirement_type],
            )
            for record in best_match.values()
        ]
        matched_courses.sort(key=lambda m: m.course_id)

        applicable_matched_credits = sum(m.credits for m in matched_courses)
        score = sum(m.ranking_points for m in matched_courses)
        major_required_credits = sum(
            m.credits for m in matched_courses if m.requirement_type == "major_required"
        )

        first = records[0]
        program_total = first.program_total_credits
        match_percentage = (
            applicable_matched_credits / program_total * 100 if program_total else None
        )
        credits_remaining = (
            program_total - applicable_matched_credits if program_total is not None else None
        )

        return ProgramRecommendation(
            program_code=first.program_code,
            program_title=first.program_title,
            credential_type=first.credential_type,
            matched_courses=matched_courses,
            applicable_matched_credits=applicable_matched_credits,
            major_required_credits_matched=major_required_credits,
            recommendation_score=score,
            match_percentage=match_percentage,
            program_total_credits=program_total,
            estimated_credits_remaining=credits_remaining,
            explanation=self._explain(matched_courses, applicable_matched_credits),
        )

    def _explain(self, matched_courses: list[MatchedCourse], applicable_matched_credits: int) -> str:
        counts: dict[str, int] = {}
        for match in matched_courses:
            counts[match.requirement_type] = counts.get(match.requirement_type, 0) + 1
        parts = [
            f"{count} as {_REQUIREMENT_TYPE_LABELS[req_type]}"
            for req_type, count in counts.items()
        ]
        return (
            f"{len(matched_courses)} course(s) matched exactly ({'; '.join(parts)}), "
            f"worth {applicable_matched_credits} potential credit(s) toward this program."
        )
