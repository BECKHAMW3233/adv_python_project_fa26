"""CourseCreditResolver -- builds a course_id -> credits reference from confirmed sources
(the FTCC program catalog and already-resolved single-course training rows), and uses it to
resolve training rows that named a course without a confirmed per-course credit value of
their own. Never invents a value: a course with no confirmed source anywhere -- in the
catalog or in any other training row -- stays unresolved."""

from __future__ import annotations

from typing import Sequence

from models import CourseCreditReference, ProgramRequirement, TrainingEquivalency


def build_reference(
    program_records: Sequence[ProgramRequirement],
    training_records: Sequence[TrainingEquivalency],
) -> dict[str, CourseCreditReference]:
    """Program-catalog values are preferred (an official FTCC-assigned credit value); an
    already-resolved single-course training row is used only for a course the catalog never
    mentions. First match wins for a given course_id -- confirmed against the real data that
    no course_id carries conflicting credit values across programs, so this is deterministic,
    not an arbitrary tie-break."""
    reference: dict[str, CourseCreditReference] = {}
    for record in program_records:
        if record.course_id and record.course_credits and record.course_id not in reference:
            reference[record.course_id] = CourseCreditReference(
                record.course_id, record.course_credits, "program_catalog"
            )
    for record in training_records:
        if (
            record.course_id
            and record.status == "ok"
            and record.course_credits
            and record.course_id not in reference
        ):
            reference[record.course_id] = CourseCreditReference(
                record.course_id, record.course_credits, f"training:{record.training_name}"
            )
    return reference


def resolve_training_credits(
    training_records: Sequence[TrainingEquivalency],
    reference: dict[str, CourseCreditReference],
) -> list[TrainingEquivalency]:
    """Fills in course_credits for any training row still marked credits_unresolved whose
    course_id is in the reference -- a row's original combined source_total_hours is
    preserved in the notes rather than discarded, and a course not found in the reference
    (nothing else in the supplied source files states its credit value) is left exactly as
    the importer produced it, still flagged for manual verification."""
    resolved: list[TrainingEquivalency] = []
    for record in training_records:
        match = reference.get(record.course_id) if record.status == "credits_unresolved" else None
        if match is None:
            resolved.append(record)
            continue
        resolved.append(
            TrainingEquivalency(
                training_id=record.training_id,
                branch=record.branch,
                training_name=record.training_name,
                training_alias=record.training_alias,
                course_id=record.course_id,
                course_credits=match.credits,
                source_total_hours=record.source_total_hours,
                verification_required=False,
                condition=record.condition,
                source_file=record.source_file,
                source_table=record.source_table,
                status="ok",
                notes=(
                    f"Credit resolved via course-credit reference ({match.source}); original "
                    f"combined total was {record.source_total_hours} hours covering multiple courses"
                ),
            )
        )
    return resolved
