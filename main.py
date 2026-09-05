"""Entry point, orchestrates the pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import cli
import pipeline
from exceptions import ReportExportError, SourceConversionError, UserBackRequested, UserExitRequested
from reports.report_generator import ReportGenerator
from services.credit_evaluator import CreditEvaluator
from services.recommendation_engine import RecommendationEngine

ROOT_DIR = Path(__file__).parent
STUDENT_REPORTS_DIR = ROOT_DIR / "student_reports"
LOGS_DIR = ROOT_DIR / "logs"

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """File-only application log (no console output, to keep the interactive UI clean).
    Never logs veteran-identifying information -- only MOS/skill-level/training codes,
    record counts, and decisions, per the spec's logging requirements."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8")],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="FTCC Military Credit and Program Recommender")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force reconversion of source files even if normalized data looks current.",
    )
    args = parser.parse_args()

    _configure_logging()

    needs_conversion, reason = pipeline.needs_conversion(args.refresh)
    logger.info(
        "Conversion decision: %s (%s)",
        "convert" if needs_conversion else "load cached",
        reason or "up to date",
    )

    if needs_conversion:
        print(f"Converting source files ({reason})...")
        try:
            records = pipeline.convert()
        except SourceConversionError as exc:
            logger.error("Conversion failed: %s: %s", type(exc).__name__, exc)
            print(f"ERROR: source conversion failed -- {exc}")
            pipeline.CONVERSION_ISSUES_DIR.mkdir(parents=True, exist_ok=True)
            (pipeline.CONVERSION_ISSUES_DIR / "fatal_conversion_error.txt").write_text(
                f"{type(exc).__name__}: {exc}\n", encoding="utf-8"
            )
            sys.exit(1)
        mos_records, mos_issues, training_records, training_issues, program_records, program_issues = records
        validation_issues = pipeline.validate_and_report(mos_records, training_records, program_records)
        pipeline.print_summary(
            mos_records,
            mos_issues,
            training_records,
            training_issues,
            program_records,
            program_issues,
            validation_issues,
        )
    else:
        print("Normalized data is current -- loading existing files without reconversion.")
        mos_records, _, training_records, _, program_records, _ = pipeline.load()
        validation_issues = pipeline.validate_and_report(mos_records, training_records, program_records)
        print(
            f"Loaded {len(mos_records)} MOS records, {len(training_records)} training records, "
            f"{len(program_records)} program requirement records."
        )
        warnings = [i for i in validation_issues if i.severity == "warning"]
        errors = [i for i in validation_issues if i.severity == "error"]
        print(f"Validation: {len(warnings)} warning(s), {len(errors)} error(s).")
        for issue in validation_issues:
            print(f"  - [{issue.severity}] {issue.source}/{issue.identifier}: {issue.message}")
        print("Run with --refresh to force reconversion from source files.")

    print()
    while True:
        try:
            mos_selections = cli.prompt_mos_selections(mos_records)
            training_ids = cli.prompt_training_selection(training_records)
            break
        except UserBackRequested:
            print("Returning to MOS selection.")
            continue
        except UserExitRequested:
            print("Exiting -- no selections made, no report generated.")
            return
    logger.info(
        "User selection: MOS=%s trainings=%d selected",
        ", ".join(f"{code}/{level}" for code, level in mos_selections),
        len(training_ids),
    )
    profile = CreditEvaluator().build_credit_profile(
        mos_records, mos_selections, training_records, training_ids
    )
    for entry in profile:
        if ";" in entry.sources:
            logger.info("Deduplicated course %s: merged sources (%s)", entry.course_id, entry.sources)
    logger.info("Credit profile built: %d distinct courses", len(profile))
    cli.print_credit_profile(profile)

    recommendations = RecommendationEngine().recommend(profile, program_records)
    logger.info(
        "Ranking complete: %s",
        ", ".join(f"{r.program_code}={r.recommendation_score}" for r in recommendations) or "no matches",
    )
    cli.print_recommendations(recommendations)

    training_names_by_id = {tid: name for tid, _branch, name in CreditEvaluator().list_trainings(training_records)}
    selected_training_names = [training_names_by_id[tid] for tid in training_ids]
    report_text = ReportGenerator().build_report_text(
        mos_selections, selected_training_names, profile, recommendations
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mos_codes_for_filename = "-".join(code for code, _level in mos_selections)
    report_path = STUDENT_REPORTS_DIR / f"recommendation_report_{mos_codes_for_filename}_{timestamp}.txt"
    try:
        ReportGenerator().export(report_text, report_path)
    except ReportExportError as exc:
        logger.error("Report export failed: %s", exc)
        print(f"ERROR: could not export report -- {exc}")
        return
    logger.info("Report exported: %s", report_path)
    print()
    print(f"Report exported to: {report_path}")


if __name__ == "__main__":
    main()
