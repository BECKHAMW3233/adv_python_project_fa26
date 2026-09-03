"""Entry point, orchestrates the pipeline."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from exceptions import InvalidSelectionError, SourceConversionError
from importers.mos_workbook_importer import MOSWorkbookImporter
from importers.program_workbook_importer import ProgramWorkbookImporter
from importers.training_docx_importer import TrainingDocxImporter
from models import (
    CreditProfileEntry,
    MOSCourseEquivalency,
    ProgramRecommendation,
    ProgramRequirement,
    TrainingEquivalency,
)
from repositories.normalized_data_repository import (
    compute_file_hash,
    read_csv,
    read_manifest,
    write_csv,
    write_manifest,
)
from reports.report_generator import ReportGenerator
from services.conversion_validator import ConversionValidator
from services.credit_evaluator import CreditEvaluator
from services.recommendation_engine import RecommendationEngine

ROOT_DIR = Path(__file__).parent
SOURCE_DATA_DIR = ROOT_DIR / "source_data"
NORMALIZED_DATA_DIR = ROOT_DIR / "normalized_data"
CONVERSION_ISSUES_DIR = ROOT_DIR / "conversion_issues"
EXPORTED_REPORTS_DIR = ROOT_DIR / "exported_reports"

MOS_SOURCE = SOURCE_DATA_DIR / "Army_MOS_Maps_Reduced.xlsx"
TRAINING_SOURCE = SOURCE_DATA_DIR / "Appendix J for website2026 (002).docx"
PROGRAM_SOURCE = SOURCE_DATA_DIR / "2026_POS_Reduced.xlsx"
SOURCE_FILES = (MOS_SOURCE, TRAINING_SOURCE, PROGRAM_SOURCE)

MOS_CSV = NORMALIZED_DATA_DIR / "mos_equivalencies.csv"
TRAINING_CSV = NORMALIZED_DATA_DIR / "training_equivalencies.csv"
PROGRAM_CSV = NORMALIZED_DATA_DIR / "program_requirements.csv"
NORMALIZED_FILES = (MOS_CSV, TRAINING_CSV, PROGRAM_CSV)

MANIFEST_PATH = NORMALIZED_DATA_DIR / ".conversion_manifest.json"


def _needs_conversion(force_refresh: bool) -> tuple[bool, str]:
    if force_refresh:
        return True, "refresh requested (--refresh)"
    if not all(path.exists() for path in NORMALIZED_FILES):
        return True, "normalized output missing"
    manifest = read_manifest(MANIFEST_PATH)
    current_hashes = {path.name: compute_file_hash(path) for path in SOURCE_FILES}
    if current_hashes != manifest:
        changed = sorted(
            name for name in current_hashes if manifest.get(name) != current_hashes[name]
        )
        return True, f"source file(s) changed: {', '.join(changed)}"
    return False, ""


def _convert() -> tuple[list, list, list, list, list, list]:
    mos_importer = MOSWorkbookImporter()
    mos_records, mos_issues = mos_importer.import_workbook(MOS_SOURCE)
    write_csv(mos_records, MOS_CSV)
    write_csv(mos_issues, CONVERSION_ISSUES_DIR / "mos_worksheet_issues.csv")

    training_importer = TrainingDocxImporter()
    training_records, training_issues = training_importer.import_document(TRAINING_SOURCE)
    write_csv(training_records, TRAINING_CSV)
    write_csv(training_issues, CONVERSION_ISSUES_DIR / "training_table_issues.csv")

    program_importer = ProgramWorkbookImporter()
    program_records, program_issues = program_importer.import_workbook(PROGRAM_SOURCE)
    write_csv(program_records, PROGRAM_CSV)
    write_csv(program_issues, CONVERSION_ISSUES_DIR / "program_workbook_issues.csv")

    write_manifest(MANIFEST_PATH, {path.name: compute_file_hash(path) for path in SOURCE_FILES})

    return (
        mos_records,
        mos_issues,
        training_records,
        training_issues,
        program_records,
        program_issues,
    )


def _load() -> tuple[list, list, list, list, list, list]:
    mos_records = read_csv(MOSCourseEquivalency, MOS_CSV)
    training_records = read_csv(TrainingEquivalency, TRAINING_CSV)
    program_records = read_csv(ProgramRequirement, PROGRAM_CSV)
    return mos_records, [], training_records, [], program_records, []


def _validate_and_report(
    mos_records: list, training_records: list, program_records: list
) -> list:
    issues = ConversionValidator().validate(mos_records, training_records, program_records)
    write_csv(issues, CONVERSION_ISSUES_DIR / "validation_issues.csv")
    return issues


def _print_summary(
    mos_records: list,
    mos_issues: list,
    training_records: list,
    training_issues: list,
    program_records: list,
    program_issues: list,
    validation_issues: list,
) -> None:
    worksheets_converted = len({(r.mos_code, r.source_sheet) for r in mos_records})
    print("SOURCE CONVERSION SUMMARY")
    print(f"MOS worksheets converted:        {worksheets_converted}")
    print(f"MOS worksheets requiring review: {len(mos_issues)}")
    print(f"MOS records written:             {len(mos_records)}")
    for issue in mos_issues:
        print(f"  - {issue.source_sheet}: {issue.message}")
    print()
    training_rows_converted = len({(r.branch, r.training_name) for r in training_records})
    print(f"Training rows converted:           {training_rows_converted}")
    print(f"Training tables requiring review:  {len(training_issues)}")
    print(f"Training records written:          {len(training_records)}")
    for issue in training_issues:
        print(f"  - {issue.source_table}: {issue.message}")
    print()
    programs_converted = len({r.program_code for r in program_records})
    print(f"Program records converted:         {programs_converted}")
    print(f"Program workbook issues:           {len(program_issues)}")
    print(f"Program requirement records:       {len(program_records)}")
    for issue in program_issues:
        print(f"  - row {issue.source_row}: {issue.message}")
    print()
    warnings = [i for i in validation_issues if i.severity == "warning"]
    errors = [i for i in validation_issues if i.severity == "error"]
    print(f"Warnings:                         {len(warnings)}")
    print(f"Errors:                           {len(errors)}")
    for issue in validation_issues:
        print(f"  - [{issue.severity}] {issue.source}/{issue.identifier}: {issue.message}")


def _prompt_mos_selection(mos_records: list) -> str:
    evaluator = CreditEvaluator()
    while True:
        query = input("Enter an MOS code or partial title: ").strip()
        matches = evaluator.find_mos_matches(mos_records, query)
        if not matches:
            print(f"No MOS found matching '{query}'. Try again.")
            continue
        if len(matches) == 1:
            code, title = matches[0]
            print(f"Matched: {code} - {title}")
            return code
        print("Multiple MOS codes matched:")
        for i, (code, title) in enumerate(matches, start=1):
            print(f"  {i}. {code} - {title}")
        selection = input("Enter the number of your MOS: ").strip()
        try:
            if not selection.isdigit():
                raise InvalidSelectionError(f"'{selection}' is not a number")
            return evaluator.select_mos_code(matches, int(selection))
        except InvalidSelectionError as exc:
            print(f"Invalid selection: {exc}")


def _prompt_skill_level(mos_records: list, mos_code: str) -> str:
    evaluator = CreditEvaluator()
    available = evaluator.available_skill_levels(mos_records, mos_code)
    print(f"Available skill levels for {mos_code}: {', '.join(available)}")
    while True:
        skill_level = input("Enter skill level: ").strip()
        try:
            return evaluator.validate_skill_level(available, skill_level)
        except InvalidSelectionError as exc:
            print(f"Invalid selection: {exc}")


def _prompt_training_selection(training_records: list) -> list[str]:
    evaluator = CreditEvaluator()
    trainings = evaluator.list_trainings(training_records)
    print("Completed trainings (enter number(s) separated by commas, or press Enter for none):")
    for i, (_training_id, branch, name) in enumerate(trainings, start=1):
        print(f"  {i}. [{branch}] {name}")
    while True:
        selection = input("Your selection: ").strip()
        try:
            return evaluator.select_trainings(trainings, selection)
        except InvalidSelectionError as exc:
            print(f"Invalid selection: {exc}")


def _print_credit_profile(profile: list[CreditProfileEntry]) -> None:
    print()
    print("POTENTIAL CREDIT SUMMARY")
    if not profile:
        print("No potential credit found for the selected MOS/skill level and trainings.")
    else:
        for entry in profile:
            print(f"  {entry.course_id}: {entry.credits} credit(s)  <- {entry.sources}")
        print(f"Total potential credits: {sum(entry.credits for entry in profile)}")
    print()
    print(
        "NOTE: this is an unofficial estimate based on documented equivalencies only. "
        "It does not guarantee that credit will be awarded or that it will apply to a "
        "specific FTCC program. Official decisions require institutional review of "
        "military documentation, current program requirements, admissions rules, "
        "credentials, substitutions, and residency requirements."
    )


def _print_recommendations(recommendations: list[ProgramRecommendation]) -> None:
    print()
    print("TOP PROGRAM RECOMMENDATIONS")
    if not recommendations:
        print("No FTCC programs had an exact course-code match against your potential credits.")
        return
    for rank, rec in enumerate(recommendations, start=1):
        print()
        print(f"#{rank}: {rec.program_code} - {rec.program_title} ({rec.credential_type})")
        print("  Matched courses:")
        for match in rec.matched_courses:
            print(
                f"    {match.course_id}: {match.credits} credit(s) -- {match.requirement_type} "
                f"(weight {match.weight}, {match.ranking_points} pts)"
            )
        print(f"  Total potentially applicable matched credits: {rec.applicable_matched_credits}")
        print(f"  Recommendation score: {rec.recommendation_score}")
        if rec.match_percentage is not None:
            print(f"  Estimated match: {rec.match_percentage:.1f}% of {rec.program_total_credits} total credits")
        if rec.estimated_credits_remaining is not None:
            print(f"  Estimated credits remaining: {rec.estimated_credits_remaining}")
        print(f"  {rec.explanation}")
    print()
    print(
        "These are estimates only, based on exact course-code matches to documented "
        "equivalencies. They do not replace an official transcript evaluation or degree audit."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="FTCC Military Credit and Program Recommender")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force reconversion of source files even if normalized data looks current.",
    )
    args = parser.parse_args()

    needs_conversion, reason = _needs_conversion(args.refresh)

    if needs_conversion:
        print(f"Converting source files ({reason})...")
        try:
            records = _convert()
        except SourceConversionError as exc:
            print(f"ERROR: source conversion failed -- {exc}")
            CONVERSION_ISSUES_DIR.mkdir(parents=True, exist_ok=True)
            (CONVERSION_ISSUES_DIR / "fatal_conversion_error.txt").write_text(
                f"{type(exc).__name__}: {exc}\n", encoding="utf-8"
            )
            sys.exit(1)
        mos_records, mos_issues, training_records, training_issues, program_records, program_issues = records
        validation_issues = _validate_and_report(mos_records, training_records, program_records)
        _print_summary(
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
        mos_records, _, training_records, _, program_records, _ = _load()
        validation_issues = _validate_and_report(mos_records, training_records, program_records)
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
    mos_code = _prompt_mos_selection(mos_records)
    skill_level = _prompt_skill_level(mos_records, mos_code)
    training_ids = _prompt_training_selection(training_records)
    profile = CreditEvaluator().build_credit_profile(
        mos_records, mos_code, skill_level, training_records, training_ids
    )
    _print_credit_profile(profile)

    recommendations = RecommendationEngine().recommend(profile, program_records)
    _print_recommendations(recommendations)

    training_names_by_id = {tid: name for tid, _branch, name in CreditEvaluator().list_trainings(training_records)}
    selected_training_names = [training_names_by_id[tid] for tid in training_ids]
    report_text = ReportGenerator().build_report_text(
        mos_code, skill_level, selected_training_names, profile, recommendations
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = EXPORTED_REPORTS_DIR / f"recommendation_report_{mos_code}_{timestamp}.txt"
    ReportGenerator().export(report_text, report_path)
    print()
    print(f"Report exported to: {report_path}")


if __name__ == "__main__":
    main()
