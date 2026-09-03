"""ReportGenerator -- console and export reports with notices."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Sequence

from models import CreditProfileEntry, ProgramRecommendation

# Verbatim "Required Notice" from the assignment spec.
REQUIRED_NOTICE = (
    "IMPORTANT: This application provides an unofficial estimate using instructional "
    "source files and student-developed conversion logic. A listed equivalency does not "
    "guarantee that credit will be awarded or apply to a specific FTCC program. Official "
    "decisions require institutional review of military documentation, current program "
    "requirements, admissions rules, credentials, substitutions, and residency requirements."
)


class ReportGenerator:
    """Builds a human-readable recommendation report and writes it to an export file."""

    def build_report_text(
        self,
        mos_code: str,
        skill_level: str,
        training_names: Sequence[str],
        profile: Sequence[CreditProfileEntry],
        recommendations: Sequence[ProgramRecommendation],
    ) -> str:
        lines: list[str] = [
            "FTCC MILITARY CREDIT AND PROGRAM RECOMMENDATION REPORT",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            "",
            f"MOS: {mos_code}   Skill level: {skill_level}",
            "Completed trainings: "
            + (", ".join(training_names) if training_names else "(none selected)"),
            "",
            "POTENTIAL CREDIT SUMMARY",
        ]

        if not profile:
            lines.append(
                "  No potential credit found for the selected MOS/skill level and trainings."
            )
        else:
            for entry in profile:
                lines.append(f"  {entry.course_id}: {entry.credits} credit(s) <- {entry.sources}")
            lines.append(f"  Total potential credits: {sum(e.credits for e in profile)}")

        lines.append("")
        lines.append("TOP PROGRAM RECOMMENDATIONS")

        if not recommendations:
            lines.append("  No FTCC programs had an exact course-code match.")
        else:
            for rank, rec in enumerate(recommendations, start=1):
                lines.append("")
                lines.append(
                    f"  #{rank}: {rec.program_code} - {rec.program_title} ({rec.credential_type})"
                )
                for match in rec.matched_courses:
                    lines.append(
                        f"      {match.course_id}: {match.credits} credit(s) -- "
                        f"{match.requirement_type} (weight {match.weight}, {match.ranking_points} pts)"
                    )
                lines.append(
                    f"      Total potentially applicable matched credits: {rec.applicable_matched_credits}"
                )
                lines.append(f"      Recommendation score: {rec.recommendation_score}")
                if rec.match_percentage is not None:
                    lines.append(
                        f"      Estimated match: {rec.match_percentage:.1f}% of "
                        f"{rec.program_total_credits} total credits"
                    )
                if rec.estimated_credits_remaining is not None:
                    lines.append(
                        f"      Estimated credits remaining: {rec.estimated_credits_remaining}"
                    )
                lines.append(f"      {rec.explanation}")

        lines.append("")
        lines.append(REQUIRED_NOTICE)
        return "\n".join(lines)

    def export(self, report_text: str, path: Path) -> None:
        """Write the report text to a file, creating parent directories as needed."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report_text, encoding="utf-8")
