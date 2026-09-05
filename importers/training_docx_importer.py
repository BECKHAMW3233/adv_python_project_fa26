"""TrainingDocxImporter -- parse training equivalency tables."""

from __future__ import annotations

import re
from pathlib import Path

import docx
from docx.table import Table

from exceptions import DocxParsingError, SourceFileNotFoundError
from models import TrainingEquivalency, TrainingTableIssue
from services.normalizer import normalize_hours, normalize_text, split_course_ids

_ALIAS_PATTERN = re.compile(r"\(([A-Z0-9][A-Z0-9 ]*[A-Z0-9])\)\s*$")
_BRANCH_HEADING_PATTERN = re.compile(r"[A-Z][A-Z ]*")


class TrainingDocxImporter:
    """Parses branch/training/FTCC-equivalency tables from the supplied Word document."""

    def import_document(
        self, path: Path
    ) -> tuple[list[TrainingEquivalency], list[TrainingTableIssue]]:
        if not path.exists():
            raise SourceFileNotFoundError(f"Training document not found: {path}")

        document = docx.Document(str(path))
        records: list[TrainingEquivalency] = []
        issues: list[TrainingTableIssue] = []
        current_branch: str | None = None

        for table_index, table in enumerate(document.tables):
            table_name = f"table_{table_index}"
            try:
                current_branch = self._parse_table(
                    table, table_name, path.name, current_branch, records
                )
            except DocxParsingError as exc:
                issues.append(TrainingTableIssue(path.name, table_name, str(exc)))

        return records, issues

    def _parse_table(
        self,
        table: Table,
        table_name: str,
        source_file: str,
        current_branch: str | None,
        records: list[TrainingEquivalency],
    ) -> str | None:
        for row in table.rows:
            cells = [normalize_text(cell.text) for cell in row.cells]
            if not any(cells):
                continue

            branch = self._match_branch_heading(cells)
            if branch:
                current_branch = branch
                continue

            if cells[0].lower() == "course name":
                continue

            if current_branch is None:
                raise DocxParsingError(
                    f"Data row in '{table_name}' appeared before any branch heading: {cells}"
                )

            records.extend(
                self._parse_data_row(cells, current_branch, source_file, table_name)
            )

        return current_branch

    def _match_branch_heading(self, cells: list[str]) -> str | None:
        first = cells[0]
        if not first or not _BRANCH_HEADING_PATTERN.fullmatch(first):
            return None
        rest = cells[1:]
        if all(cell in ("", first) for cell in rest):
            return first
        return None

    def _parse_data_row(
        self, cells: list[str], branch: str, source_file: str, table_name: str
    ) -> list[TrainingEquivalency]:
        if len(cells) < 3 or not cells[0]:
            return []
        training_name, equivalency_raw, hours_raw = cells[0], cells[1], cells[2]

        alias_match = _ALIAS_PATTERN.search(training_name)
        training_alias = alias_match.group(1) if alias_match else ""

        course_ids = split_course_ids(equivalency_raw)
        source_total_hours = normalize_hours(hours_raw)
        training_id = re.sub(
            r"[^A-Z0-9]+", "_", f"{branch}_{training_name}".upper()
        ).strip("_")

        if not course_ids:
            return [
                TrainingEquivalency(
                    training_id=training_id,
                    branch=branch,
                    training_name=training_name,
                    training_alias=training_alias,
                    course_id="",
                    course_credits=None,
                    source_total_hours=source_total_hours,
                    verification_required=True,
                    condition="",
                    source_file=source_file,
                    source_table=table_name,
                    status="no_equivalency_found",
                    notes=f"Could not parse an FTCC course ID from '{equivalency_raw}'",
                )
            ]

        single_course = len(course_ids) == 1
        return [
            TrainingEquivalency(
                training_id=training_id,
                branch=branch,
                training_name=training_name,
                training_alias=training_alias,
                course_id=course_id,
                course_credits=source_total_hours if single_course else None,
                source_total_hours=source_total_hours,
                verification_required=not single_course,
                condition="",
                source_file=source_file,
                source_table=table_name,
                status="ok" if single_course else "credits_unresolved",
                notes=(
                    ""
                    if single_course
                    else "Combined hours cover multiple courses; per-course credit "
                    "not invented, see source_total_hours"
                ),
            )
            for course_id in course_ids
        ]
