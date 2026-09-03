"""ConversionValidator -- validate schema and create issue reports."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from models import (
    MOSCourseEquivalency,
    ProgramRequirement,
    TrainingEquivalency,
    ValidationIssue,
)
from services.normalizer import is_valid_course_id


class ConversionValidator:
    """Validates normalized records after conversion and reports schema/integrity issues."""

    def validate(
        self,
        mos_records: Sequence[MOSCourseEquivalency],
        training_records: Sequence[TrainingEquivalency],
        program_records: Sequence[ProgramRequirement],
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        issues.extend(self._validate_mos(mos_records))
        issues.extend(self._validate_training(training_records))
        issues.extend(self._validate_program(program_records))
        return issues

    def _validate_mos(self, records: Sequence[MOSCourseEquivalency]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        seen: Counter[tuple[str, str, str]] = Counter()
        for record in records:
            identifier = f"{record.mos_code}/{record.skill_level}/{record.course_id}"
            if not record.mos_code or not record.skill_level or not record.course_id:
                issues.append(
                    ValidationIssue(
                        "error",
                        "mos",
                        identifier,
                        "Missing required field (mos_code, skill_level, or course_id)",
                    )
                )
                continue
            if not is_valid_course_id(record.course_id):
                issues.append(
                    ValidationIssue(
                        "error",
                        "mos",
                        identifier,
                        f"Course ID '{record.course_id}' does not match normalized format",
                    )
                )
            if record.credits < 0:
                issues.append(
                    ValidationIssue(
                        "error", "mos", identifier, f"Negative credits ({record.credits})"
                    )
                )
            seen[(record.mos_code, record.skill_level, record.course_id)] += 1

        for (mos_code, skill_level, course_id), count in seen.items():
            if count > 1:
                issues.append(
                    ValidationIssue(
                        "error",
                        "mos",
                        f"{mos_code}/{skill_level}/{course_id}",
                        f"Duplicated {count} times (same MOS/skill level/course)",
                    )
                )
        return issues

    def _validate_training(
        self, records: Sequence[TrainingEquivalency]
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for record in records:
            identifier = record.training_id or "(missing training_id)"
            if not record.training_id or not record.branch or not record.training_name:
                issues.append(
                    ValidationIssue(
                        "error",
                        "training",
                        identifier,
                        "Missing required field (training_id, branch, or training_name)",
                    )
                )
            if not record.course_id and record.status != "no_equivalency_found":
                issues.append(
                    ValidationIssue(
                        "warning",
                        "training",
                        identifier,
                        "Missing course_id without a no_equivalency_found status to explain it",
                    )
                )
            if record.course_id and not is_valid_course_id(record.course_id):
                issues.append(
                    ValidationIssue(
                        "error",
                        "training",
                        identifier,
                        f"Course ID '{record.course_id}' does not match normalized format",
                    )
                )
            if record.course_credits is not None and record.course_credits < 0:
                issues.append(
                    ValidationIssue(
                        "error",
                        "training",
                        identifier,
                        f"Negative credits ({record.course_credits})",
                    )
                )
        return issues

    def _validate_program(
        self, records: Sequence[ProgramRequirement]
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for record in records:
            identifier = f"{record.program_code}/row{record.source_row}/{record.course_id}"
            if not record.program_code or not record.course_id:
                issues.append(
                    ValidationIssue(
                        "error",
                        "program",
                        identifier,
                        "Missing required field (program_code or course_id)",
                    )
                )
                continue
            if not record.program_title:
                issues.append(
                    ValidationIssue(
                        "error",
                        "program",
                        identifier,
                        f"Program code '{record.program_code}' has no known title/metadata "
                        "-- does not belong to a recognized program header",
                    )
                )
            if not is_valid_course_id(record.course_id):
                issues.append(
                    ValidationIssue(
                        "error",
                        "program",
                        identifier,
                        f"Course ID '{record.course_id}' does not match normalized format",
                    )
                )
            if record.course_credits < 0:
                issues.append(
                    ValidationIssue(
                        "error", "program", identifier, f"Negative credits ({record.course_credits})"
                    )
                )
            if record.requirement_type == "unresolved" and record.status != "manual_review":
                issues.append(
                    ValidationIssue(
                        "warning",
                        "program",
                        identifier,
                        "Unresolved requirement_type without a manual_review status to explain it",
                    )
                )
        return issues
