"""Interactive CLI prompting and console display -- MOS/skill-level/training selection
and the credit-profile/recommendation output. Split out of main.py so entry-point/pipeline
concerns and interactive-CLI concerns aren't mixed in one file."""

from __future__ import annotations

import shutil

from exceptions import InvalidSelectionError, UserBackRequested, UserExitRequested
from models import CreditProfileEntry, ProgramRecommendation
from reports.report_generator import surplus_note
from services.credit_evaluator import CreditEvaluator


def _check_navigation(raw_input: str) -> None:
    """Raise UserExitRequested/UserBackRequested if raw_input is a navigation keyword
    (case-insensitive), so every prompt can check its raw text the same way before parsing
    it as an actual answer."""
    normalized = raw_input.strip().lower()
    if normalized == "exit":
        raise UserExitRequested()
    if normalized == "back":
        raise UserBackRequested()


def print_columns(items: list[str]) -> None:
    """Print a numbered list in a multi-column grid (top-to-bottom per column, then wrapping
    right) so a long list fits on screen without one item per line. Column width is capped
    rather than sized to the single longest item, since a handful of unusually long names
    would otherwise force everything down to one column -- the rare long entry just spills
    into the next column's space on its own row instead."""
    if not items:
        return
    terminal_width = shutil.get_terminal_size(fallback=(100, 24)).columns
    col_width = min(max(len(item) for item in items) + 2, 46)
    columns = max(1, terminal_width // col_width)
    rows = -(-len(items) // columns)  # ceil division
    for row in range(rows):
        line = ""
        for col in range(columns):
            index = col * rows + row
            if index < len(items):
                line += items[index].ljust(col_width)
        print(line.rstrip())


def prompt_mos_selection(mos_records: list) -> str:
    evaluator = CreditEvaluator()
    while True:
        query = input("Enter an MOS code or partial title (or 'back'/'exit'): ").strip()
        _check_navigation(query)
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
        selection = input("Enter the number of your MOS (or 'back'/'exit'): ").strip()
        try:
            _check_navigation(selection)
            if not selection.isdigit():
                raise InvalidSelectionError(f"'{selection}' is not a number")
            return evaluator.select_mos_code(matches, int(selection))
        except UserBackRequested:
            continue
        except InvalidSelectionError as exc:
            print(f"Invalid selection: {exc}")


def prompt_skill_level(mos_records: list, mos_code: str) -> str:
    evaluator = CreditEvaluator()
    available = evaluator.available_skill_levels(mos_records, mos_code)
    print(f"Available skill levels for {mos_code}: {', '.join(available)}")
    while True:
        skill_level = input("Enter skill level (or 'back'/'exit'): ").strip()
        _check_navigation(skill_level)
        try:
            return evaluator.validate_skill_level(available, skill_level)
        except InvalidSelectionError as exc:
            print(f"Invalid selection: {exc}")


def prompt_mos_selections(mos_records: list) -> list[tuple[str, str]]:
    """Loop: match an MOS, pick its skill level, then ask whether to add another -- some
    veterans hold more than one MOS by the time they leave service (e.g. after
    reclassification), so the credit profile needs to draw from more than one.
    'back' while picking an MOS or its skill level restarts that MOS's entry; 'back' at the
    add-another prompt undoes the MOS just added and lets you redo it."""
    selections: list[tuple[str, str]] = []
    while True:
        try:
            mos_code = prompt_mos_selection(mos_records)
            skill_level = prompt_skill_level(mos_records, mos_code)
        except UserBackRequested:
            continue
        if (mos_code, skill_level) in selections:
            print(f"Already added {mos_code} at skill level {skill_level} -- skipping duplicate.")
        else:
            selections.append((mos_code, skill_level))
        print(
            "MOS selections so far: "
            + ", ".join(f"{code} ({level})" for code, level in selections)
        )
        again = input("Add another MOS? (y/n, or 'back'/'exit'): ").strip()
        try:
            _check_navigation(again)
        except UserBackRequested:
            if selections:
                removed_code, removed_level = selections.pop()
                print(f"Removed {removed_code} ({removed_level}) -- re-enter it or a different MOS.")
            continue
        if again.lower() != "y":
            return selections


def prompt_training_selection(training_records: list) -> list[str]:
    """Branch-first menu: pick a branch, select trainings from its (much shorter) list, then
    either pick another branch or finish. Selections accumulate across branches. Kept as a
    menu rather than one flat list of all trainings, since that list is expected to keep
    growing as more branches/schools are added to the source data over the semester.
    'back' at the branch menu exits this whole step (there's no earlier step within training
    selection to return to); 'back' while picking a branch's trainings returns to the branch
    menu without selecting anything from it."""
    evaluator = CreditEvaluator()
    branches = evaluator.list_branches(training_records)
    done_choice = len(branches) + 1
    selected_ids: list[str] = []

    while True:
        print()
        print("Select a branch to see its trainings:")
        for i, branch in enumerate(branches, start=1):
            print(f"  {i}. {branch}")
        print(f"  {done_choice}. Done -- finish training selection ({len(selected_ids)} selected so far)")
        choice = input("Your selection (or 'back'/'exit'): ").strip()
        _check_navigation(choice)

        if not choice.isdigit():
            print(f"Invalid selection: '{choice}' is not a number")
            continue
        choice_num = int(choice)
        if choice_num == done_choice:
            return selected_ids
        try:
            branch = evaluator.select_branch(branches, choice_num)
        except InvalidSelectionError as exc:
            print(f"Invalid selection: {exc}")
            continue

        branch_trainings = evaluator.list_trainings_for_branch(training_records, branch)
        print(f"Completed {branch} trainings (enter number(s) separated by commas, or press Enter for none):")
        print_columns(
            [f"{i}. {name}" for i, (_training_id, _branch, name) in enumerate(branch_trainings, start=1)]
        )
        try:
            new_ids = _prompt_training_numbers(branch_trainings)
        except UserBackRequested:
            continue
        for training_id in new_ids:
            if training_id not in selected_ids:
                selected_ids.append(training_id)


def _prompt_training_numbers(branch_trainings: list[tuple[str, str, str]]) -> list[str]:
    evaluator = CreditEvaluator()
    while True:
        selection = input("Your selection (or 'back'/'exit'): ").strip()
        _check_navigation(selection)
        try:
            return evaluator.select_trainings(branch_trainings, selection)
        except InvalidSelectionError as exc:
            print(f"Invalid selection: {exc}")


def print_credit_profile(profile: list[CreditProfileEntry]) -> None:
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


def print_recommendations(recommendations: list[ProgramRecommendation]) -> None:
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
        note = surplus_note(rec.surplus_courses)
        if note:
            print(f"  {note}")
    print()
    print(
        "These are estimates only, based on exact course-code matches to documented "
        "equivalencies. They do not replace an official transcript evaluation or degree audit."
    )
