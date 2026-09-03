"""ProgramWorkbookImporter -- parse report-oriented program blocks and rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import openpyxl

from exceptions import SourceFileNotFoundError
from models import ProgramRequirement, ProgramWorkbookIssue
from services.normalizer import normalize_text

_ID_COLUMN_LIMIT = 22  # term column index; everything before this may hold wrapped label/ID text

_PROGRAM_HEADER_PATTERN = re.compile(
    r"Program of Study:\s*(?P<title>.+?)\s*\((?P<code>[A-Z]\d{5})\)\s*Type:\s*(?P<credential>\S+)"
)
_CATALOG_YEAR_PATTERN = re.compile(r"Catalog:\s*(?P<year>\d{4})\s*Catalog Year")
_GROUP_HEADER_PATTERN = re.compile(
    r"(?<![\d.])(?P<num>\d{1,2})\)\s+(?P<name>[A-Za-z][A-Za-z /]*?)\s*\(\s*(?P<total>\d+\.\d{2})\s*\)"
)
# Looser than _GROUP_HEADER_PATTERN: a group's own total is often NOT inline (it can land in a
# string-typed hour cell instead, e.g. Welding Technology's "2) Major Requirements..." group has
# no "(XX.XX)" in the text at all). This still needs to catch the group-number transition even
# when no total is present, so it doesn't require one -- _GROUP_HEADER_PATTERN above is kept
# separately, purely to exclude genuine inline group-totals from the program-total scan below.
_GROUP_NUMBER_PATTERN = re.compile(
    r"(?<![\d.])(?P<num>\d{1,2})\)\s+(?P<name>[A-Za-z][A-Za-z0-9 /&.]*)"
)
_STANDALONE_TOTAL_PATTERN = re.compile(r"\(\s*(?P<total>\d+\.\d{2})\s*\)")
_SUBGROUP_LABEL_PATTERN = re.compile(
    r"(?P<label>[A-Za-z][A-Za-z0-9 /&]*?\b(?:Pick|Courses))\b", re.IGNORECASE
)
_NESTED_PATTERN = re.compile(r"\bGroups?\b|\bSubrequirement", re.IGNORECASE)
_SIMPLE_COURSE_PATTERN = re.compile(r"\b([A-Z]{2,4}-\d{3})\b")
_FLATTENED_COURSE_PATTERN = re.compile(
    r"S\d+\s+(?P<course>[A-Z]{2,4}-\d{3})\s+\d{4}[A-Z]{2}\s+.*?"
    r"(?P<class>\d+\.\d{2})\s+(?P<lab>\d+\.\d{2})\s+(?P<clinic>\d+\.\d{2})\s+(?P<credits>\d+\.\d{2})"
)
_TRAILING_DECIMAL_PATTERN = re.compile(r"(\d+\.\d{2})\s*$")
_LEADING_PAREN_TOTAL_PATTERN = re.compile(r"^\(\s*(\d+\.\d{2})\s*\)")


@dataclass
class _State:
    program_code: str | None = None
    requirement_group: str = ""
    subgroup_label: str = ""
    subgroup_type: str = ""  # "direct" | "choice" | ""
    nested: bool = False


@dataclass
class _Event:
    position: int
    kind: str  # "group" | "subgroup" | "total" | "course"
    name: str = ""
    subgroup_type: str = ""
    nested: bool = False
    total: float | None = None
    course_id: str = ""
    credits: int | None = None


def _is_num(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _build_blob(row: tuple) -> str:
    """Concatenate every text-column fragment before the term column into one blob.

    Deeply indented rows wrap their label text across two or more columns (e.g. a Pick
    group's category name in column 0 and its continuation in column 8); rather than try
    to reconstruct exact original line breaks -- which turned out to be genuinely
    ambiguous for a handful of rows -- every fragment is joined into one blob and matched
    against with regexes, which is robust to that ambiguity.
    """
    fragments = [
        cell.replace("\n", " ")
        for cell in row[:_ID_COLUMN_LIMIT]
        if isinstance(cell, str) and cell.strip()
    ]
    return normalize_text(" ".join(fragments))


def _row_hours(row: tuple) -> tuple[int | None, float | None]:
    """Returns (credits, incidental_total).

    Credits is normally the last of the Class/Lab/Clinic/Credits numeric cells in the row.
    Occasionally a group/program total lands inside the same cell as the credits value
    (e.g. '(33.00)\\n3.00'), so string-typed hour-zone cells are also checked for a leading
    parenthetical total and a trailing plain number.
    """
    numeric_values: list[float] = []
    incidental_total: float | None = None
    for cell in row[40:]:
        if _is_num(cell):
            numeric_values.append(float(cell))
        elif isinstance(cell, str):
            paren_match = _LEADING_PAREN_TOTAL_PATTERN.match(cell.strip())
            if paren_match:
                incidental_total = float(paren_match.group(1))
            trailing_match = _TRAILING_DECIMAL_PATTERN.search(cell)
            if trailing_match:
                numeric_values.append(float(trailing_match.group(1)))
    if not numeric_values:
        return None, incidental_total
    return int(numeric_values[-1]), incidental_total


def _footer_total(row: tuple) -> float | None:
    """A program's total credits occasionally appears as a lone negative int in its own
    row -- Excel's accounting-style number format renders a negative number in
    parentheses, so the raw stored value is the total, sign-flipped."""
    populated = [cell for cell in row if cell is not None]
    if len(populated) == 1:
        value = populated[0]
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value < 0:
            return abs(float(value))
    return None


def _collect_events(blob: str, row: tuple, is_structured: bool) -> list[_Event]:
    """Extract group/subgroup/total/course events from a row's blob, in the order they
    appear in the text. Position-ordering matters: a row can contain a course belonging
    to the group that's ENDING (e.g. the last course of a direct-required list, flattened
    together with the next Pick group's header) as well as a row where a new group's
    header appears before its own first course -- the two look structurally similar but
    need the state update applied before or after the course event respectively.
    """
    events: list[_Event] = []

    for match in _GROUP_NUMBER_PATTERN.finditer(blob):
        events.append(
            _Event(position=match.start(), kind="group", name=normalize_text(match.group("name")))
        )

    group_spans = [m.span() for m in _GROUP_HEADER_PATTERN.finditer(blob)]

    for match in _STANDALONE_TOTAL_PATTERN.finditer(blob):
        overlaps_group = any(
            match.start() >= start and match.end() <= end for start, end in group_spans
        )
        if overlaps_group:
            continue
        events.append(
            _Event(position=match.start(), kind="total", total=float(match.group("total")))
        )

    for match in _SUBGROUP_LABEL_PATTERN.finditer(blob):
        label = normalize_text(match.group("label"))
        subgroup_type = "choice" if re.search(r"\bpick\b", label, re.IGNORECASE) else "direct"
        nested = bool(_NESTED_PATTERN.search(blob[max(0, match.start() - 40) : match.end() + 60]))
        events.append(
            _Event(
                position=match.start(),
                kind="subgroup",
                name=label,
                subgroup_type=subgroup_type,
                nested=nested,
            )
        )

    if is_structured:
        match = _SIMPLE_COURSE_PATTERN.search(blob)
        if match:
            # incidental_total (a group-level total that occasionally lands in the same
            # cell as credits) is intentionally not used -- program_total_credits is
            # sourced only from the dedicated footer/standalone-total patterns, so a
            # group-level figure here can't be allowed to overwrite it.
            credits, _incidental_total = _row_hours(row)
            events.append(
                _Event(
                    position=match.start(),
                    kind="course",
                    course_id=match.group(1).replace("-", "").replace(" ", "").upper(),
                    credits=credits if credits is not None else 0,
                )
            )
    else:
        for match in _FLATTENED_COURSE_PATTERN.finditer(blob):
            events.append(
                _Event(
                    position=match.start(),
                    kind="course",
                    course_id=match.group("course").replace("-", "").replace(" ", "").upper(),
                    credits=int(float(match.group("credits"))),
                )
            )

    events.sort(key=lambda e: e.position)
    return events


def _classify(state: _State) -> str:
    """Maps a course's current group/subgroup state to the spec's three requirement-type
    categories. Every General-Education-labeled group maps to general_education_choice
    (the spec doesn't define a separate "required" gen-ed category); everything else is
    major_choice or major_required depending on whether it's a Pick group or a direct
    list."""
    if not state.requirement_group:
        return "unresolved"
    if "general education" in state.requirement_group.lower():
        return "general_education_choice"
    if state.subgroup_type == "choice":
        return "major_choice"
    if state.subgroup_type == "direct":
        return "major_required"
    return "unresolved"


class ProgramWorkbookImporter:
    """Discovers program blocks in the report-style FTCC programs-of-study workbook and parses their requirement rules."""

    def import_workbook(
        self, path: Path
    ) -> tuple[list[ProgramRequirement], list[ProgramWorkbookIssue]]:
        if not path.exists():
            raise SourceFileNotFoundError(f"Program workbook not found: {path}")

        workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
        worksheet = workbook.worksheets[0]
        rows = list(worksheet.iter_rows(values_only=True))

        records: list[ProgramRequirement] = []
        issues: list[ProgramWorkbookIssue] = []
        program_totals: dict[str, float] = {}
        program_meta: dict[str, tuple[str, str, str]] = {}

        state = _State()

        for row_index, row in enumerate(rows):
            if row is None or all(cell is None for cell in row):
                continue

            footer_total = _footer_total(row)
            if footer_total is not None:
                if state.program_code:
                    program_totals[state.program_code] = footer_total
                continue

            blob = _build_blob(row)
            if not blob:
                continue

            program_match = _PROGRAM_HEADER_PATTERN.search(blob)
            if program_match:
                code = program_match.group("code")
                if code != state.program_code:
                    state = _State(program_code=code)
                    title = normalize_text(program_match.group("title"))
                    credential = program_match.group("credential")
                    year_match = _CATALOG_YEAR_PATTERN.search(blob)
                    catalog_year = year_match.group("year") if year_match else ""
                    program_meta[code] = (title, credential, catalog_year)
                # A repeated page-header cell occasionally has the program's total
                # credits appended to it (e.g. Graphic Design's "page 3" header ends in
                # "(69.00)"), so still check for a standalone total before moving on.
                total_match = _STANDALONE_TOTAL_PATTERN.search(blob, program_match.end())
                if total_match:
                    program_totals[state.program_code] = float(total_match.group("total"))
                continue

            if re.fullmatch(r"Class\s+Lab\s+Clinc/Exp\s+Credits", blob):
                continue

            if state.program_code is None:
                issues.append(
                    ProgramWorkbookIssue(
                        path.name,
                        row_index,
                        f"Row content before any program header: {blob[:120]}",
                    )
                )
                continue

            is_structured = len(row) > _ID_COLUMN_LIMIT and row[_ID_COLUMN_LIMIT] is not None

            for event in _collect_events(blob, row, is_structured):
                if event.kind == "group":
                    state.requirement_group = event.name
                elif event.kind == "subgroup":
                    state.subgroup_label = event.name
                    state.subgroup_type = event.subgroup_type
                    state.nested = event.nested
                elif event.kind == "total":
                    program_totals[state.program_code] = event.total
                elif event.kind == "course":
                    requirement_type = _classify(state)
                    title, credential, catalog_year = program_meta.get(
                        state.program_code, ("", "", "")
                    )
                    records.append(
                        ProgramRequirement(
                            program_code=state.program_code,
                            program_title=title,
                            credential_type=credential,
                            catalog_year=catalog_year,
                            program_total_credits=None,
                            requirement_group=state.requirement_group,
                            requirement_type=requirement_type,
                            course_id=event.course_id,
                            course_credits=event.credits or 0,
                            source_file=path.name,
                            source_row=row_index,
                            raw_rule_text=blob,
                            status="manual_review" if state.nested else "ok",
                            notes=(
                                "Nested multi-level choice structure not modeled; "
                                "requirement type not classified"
                                if state.nested
                                else ""
                            ),
                        )
                    )

        for record in records:
            record.program_total_credits = program_totals.get(record.program_code)

        return records, issues
