"""ReportGenerator -- console and export reports with notices."""

from __future__ import annotations

import textwrap
from datetime import datetime
from pathlib import Path
from typing import Sequence

from exceptions import ReportExportError
from models import CreditProfileEntry, MatchedCourse, ProgramRecommendation

# Verbatim "Required Notice" from the assignment spec.
REQUIRED_NOTICE = (
    "This application provides an unofficial estimate using instructional "
    "source files and student-developed conversion logic. A listed equivalency does not "
    "guarantee that credit will be awarded or apply to a specific FTCC program. Official "
    "decisions require institutional review of military documentation, current program "
    "requirements, admissions rules, credentials, substitutions, and residency requirements."
)

_WIDTH = 80
_DIVIDER = "=" * _WIDTH
_RULE = "-" * _WIDTH


def _wrap(text: str, indent: str = "") -> list[str]:
    return textwrap.wrap(
        text, width=_WIDTH - len(indent), initial_indent=indent, subsequent_indent=indent
    ) or [indent.rstrip()]


def surplus_note(surplus_courses: Sequence[MatchedCourse]) -> str:
    """Advisory text for courses that qualify for a requirement but weren't counted
    because the requirement's target is already met by a higher-value course. Kept as a
    shared helper so console display and the exported report say the same thing, built
    directly from the structured surplus_courses list rather than a string to re-parse."""
    if not surplus_courses:
        return ""
    surplus_ids = ", ".join(match.course_id for match in surplus_courses)
    return (
        f"Also holds: {surplus_ids} -- qualifies for the same requirement but isn't "
        "counted since it's already satisfied. Consult an FTCC advisor about which "
        "option best fits your plans if you intend to transfer to a 4-year program."
    )


class ReportGenerator:
    """Builds a human-readable recommendation report and writes it to an export file."""

    def build_report_text(
        self,
        mos_selections: Sequence[tuple[str, str]],
        training_names: Sequence[str],
        profile: Sequence[CreditProfileEntry],
        recommendations: Sequence[ProgramRecommendation],
    ) -> str:
        lines: list[str] = [
            _DIVIDER,
            "FTCC MILITARY CREDIT AND PROGRAM RECOMMENDATION REPORT",
            _DIVIDER,
            f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            "",
            "YOUR SELECTIONS",
            _RULE,
            "MOS:",
        ]
        for mos_code, skill_level in mos_selections:
            lines.append(f"  {mos_code}  (skill level {skill_level})")
        lines.append(
            "Completed Trainings:  "
            + (", ".join(training_names) if training_names else "(none selected)")
        )
        lines.append("")
        lines.append("POTENTIAL CREDIT SUMMARY")
        lines.append(_RULE)

        if not profile:
            lines.append(
                "No potential credit found for the selected MOS/skill level and trainings."
            )
        else:
            lines.append(f"{'Course':<10} {'Credits':<8} Source")
            for entry in profile:
                lines.append(f"{entry.course_id:<10} {entry.credits:<8} {entry.sources}")
            lines.append(_RULE)
            lines.append(f"Total Potential Credits: {sum(entry.credits for entry in profile)}")

        lines.append("")
        lines.append("TOP PROGRAM RECOMMENDATIONS")
        lines.append(_RULE)

        if not recommendations:
            lines.append("No FTCC programs had an exact course-code match.")
        else:
            for rank, rec in enumerate(recommendations, start=1):
                lines.append("")
                lines.append(
                    f"#{rank}  {rec.program_code} - {rec.program_title} ({rec.credential_type})"
                )
                lines.append("")
                lines.append("    Matched Courses:")
                for match in rec.matched_courses:
                    lines.append(
                        f"      {match.course_id:<8} {match.credits:>2} cr   "
                        f"{match.requirement_type:<26} (weight {match.weight}, "
                        f"{match.ranking_points} pts)"
                    )
                lines.append("")
                lines.append(f"    Matched Credits:       {rec.applicable_matched_credits}")
                lines.append(f"    Recommendation Score:  {rec.recommendation_score}")
                if rec.match_percentage is not None:
                    lines.append(
                        f"    Estimated Match:       {rec.match_percentage:.1f}% of "
                        f"{rec.program_total_credits} total credits"
                    )
                if rec.estimated_credits_remaining is not None:
                    lines.append(f"    Credits Remaining:     {rec.estimated_credits_remaining}")
                lines.append("")
                lines.extend(_wrap(rec.explanation, indent="    "))
                note = surplus_note(rec.surplus_courses)
                if note:
                    lines.append("")
                    lines.extend(_wrap(note, indent="    "))

        lines.append("")
        lines.append(_DIVIDER)
        lines.append("IMPORTANT NOTICE")
        lines.append(_DIVIDER)
        lines.extend(_wrap(REQUIRED_NOTICE))

        return "\n".join(lines)

    def export(self, report_text: str, path: Path) -> None:
        """Write the report text to a file, creating parent directories as needed."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report_text, encoding="utf-8")
        except OSError as exc:
            raise ReportExportError(f"Could not export report to {path}: {exc}") from exc
