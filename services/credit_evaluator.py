"""CreditEvaluator -- combine MOS and training equivalencies; deduplicate."""

from __future__ import annotations

from typing import Sequence

from exceptions import InvalidSelectionError
from models import CreditProfileEntry, MOSCourseEquivalency, TrainingEquivalency


class CreditEvaluator:
    """Pure selection, matching, and combination logic for the MOS/training credit profile.

    Deliberately contains no input()/print() calls -- the interactive prompting loop lives in
    main.py, so this class can be exercised directly in tests without mocking stdin.
    """

    def find_mos_matches(
        self, mos_records: Sequence[MOSCourseEquivalency], query: str
    ) -> list[tuple[str, str]]:
        """Distinct (mos_code, mos_title) pairs where the code or title contains query (case-insensitive)."""
        query_lower = query.strip().lower()
        matches: dict[str, str] = {}
        for record in mos_records:
            if query_lower in record.mos_code.lower() or query_lower in record.mos_title.lower():
                matches[record.mos_code] = record.mos_title
        return sorted(matches.items())

    def select_mos_code(self, matches: Sequence[tuple[str, str]], selection: int) -> str:
        if not (1 <= selection <= len(matches)):
            raise InvalidSelectionError(
                f"'{selection}' is not a valid choice (expected 1-{len(matches)})"
            )
        return matches[selection - 1][0]

    def available_skill_levels(
        self, mos_records: Sequence[MOSCourseEquivalency], mos_code: str
    ) -> list[str]:
        """Distinct skill levels present for a given MOS code, sorted numerically."""
        levels = {record.skill_level for record in mos_records if record.mos_code == mos_code}
        return sorted(levels, key=lambda level: (len(level), level))

    def validate_skill_level(self, available: Sequence[str], skill_level: str) -> str:
        skill_level = skill_level.strip()
        if skill_level not in available:
            raise InvalidSelectionError(
                f"'{skill_level}' is not an available skill level ({', '.join(available)})"
            )
        return skill_level

    def list_trainings(
        self, training_records: Sequence[TrainingEquivalency]
    ) -> list[tuple[str, str, str]]:
        """Distinct (training_id, branch, training_name) trainings, for display as a numbered list."""
        seen: dict[str, tuple[str, str, str]] = {}
        for record in training_records:
            seen.setdefault(
                record.training_id, (record.training_id, record.branch, record.training_name)
            )
        return sorted(seen.values(), key=lambda item: (item[1], item[2]))

    def list_branches(self, training_records: Sequence[TrainingEquivalency]) -> list[str]:
        """Distinct branches present in the training data, sorted."""
        return sorted({record.branch for record in training_records})

    def select_branch(self, branches: Sequence[str], selection: int) -> str:
        if not (1 <= selection <= len(branches)):
            raise InvalidSelectionError(
                f"'{selection}' is not a valid choice (expected 1-{len(branches)})"
            )
        return branches[selection - 1]

    def list_trainings_for_branch(
        self, training_records: Sequence[TrainingEquivalency], branch: str
    ) -> list[tuple[str, str, str]]:
        """Distinct (training_id, branch, training_name) trainings for one branch only."""
        return [t for t in self.list_trainings(training_records) if t[1] == branch]

    def select_trainings(
        self, trainings: Sequence[tuple[str, str, str]], selection_text: str
    ) -> list[str]:
        """Parse a comma-separated list of 1-based training numbers into training_ids.
        An empty/blank selection means "no completed trainings" and returns []."""
        selection_text = selection_text.strip()
        if not selection_text:
            return []
        training_ids: list[str] = []
        for piece in selection_text.split(","):
            piece = piece.strip()
            if not piece.isdigit():
                raise InvalidSelectionError(f"'{piece}' is not a valid training number")
            index = int(piece)
            if not (1 <= index <= len(trainings)):
                raise InvalidSelectionError(
                    f"'{index}' is not a valid training number (expected 1-{len(trainings)})"
                )
            training_ids.append(trainings[index - 1][0])
        return training_ids

    def build_credit_profile(
        self,
        mos_records: Sequence[MOSCourseEquivalency],
        mos_code: str,
        skill_level: str,
        training_records: Sequence[TrainingEquivalency],
        selected_training_ids: Sequence[str],
    ) -> list[CreditProfileEntry]:
        """Combine the selected MOS/skill-level equivalencies and selected trainings' equivalencies
        into one deduplicated potential-credit profile. When more than one source grants credit for
        the same course, every contributing source is preserved and the higher credit value is kept
        (the same course is only ever counted once toward the total, never summed across sources)."""
        by_course: dict[str, CreditProfileEntry] = {}

        def _add(course_id: str, credits: int, source: str) -> None:
            if credits <= 0:
                return
            entry = by_course.get(course_id)
            if entry is None:
                by_course[course_id] = CreditProfileEntry(course_id, credits, source)
            else:
                entry.credits = max(entry.credits, credits)
                entry.sources = f"{entry.sources}; {source}"

        for record in mos_records:
            if record.mos_code == mos_code and record.skill_level == skill_level:
                _add(record.course_id, record.credits, f"MOS {mos_code} skill level {skill_level}")

        selected_ids = set(selected_training_ids)
        for record in training_records:
            if record.training_id in selected_ids and record.course_credits is not None:
                _add(record.course_id, record.course_credits, f"Training: {record.training_name}")

        return sorted(by_course.values(), key=lambda entry: entry.course_id)
