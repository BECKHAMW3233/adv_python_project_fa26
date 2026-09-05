# Changelog

## [26] 2026-09-05 — Add 'exit' and 'back' navigation to every interactive prompt

**Why:** per William's direction -- there was no fast way to quit the program mid-flow, or to correct an earlier answer without restarting the whole interactive session.

- Added `UserExitRequested` and `UserBackRequested` (`exceptions.py`); `cli._check_navigation()` raises the appropriate one whenever a prompt's raw input is `"exit"` or `"back"` (case-insensitive), checked before that prompt tries to parse the input as a real answer. Every `input()` call in `cli.py` now checks for these.
- Since there's no menu "stack," each prompt either handles `back` locally (retrying its own earlier step) or lets it propagate to its caller, whose loop retries from its own start: the MOS number-selection list retries the MOS query; skill-level entry (no earlier step of its own) propagates up to redo MOS selection; the "Add another MOS?" prompt undoes the MOS just added and lets it be redone; a branch's training-number entry returns to the branch menu; the branch menu itself (top of training selection, nothing earlier within that step) propagates all the way to `main()`, which restarts MOS selection from scratch.
- `main()` wraps the MOS+training selection phase in a loop: `UserBackRequested` from the training branch menu re-runs MOS selection then re-enters training selection; `UserExitRequested` from anywhere prints a message and ends the program immediately, with no report generated.

Verified with 8 separate manual CLI runs via piped stdin, one per behavior: `exit` at the very first prompt and mid-flow (skill-level entry) both end cleanly with no traceback and exit code 0; `back` at a multi-match MOS list retries the query; `back` during skill-level entry discards the picked MOS and retries MOS selection; `back` at "Add another MOS?" removes the just-added MOS and lets it be re-entered (confirmed the replacement value took effect); `back` at the training branch menu discards the MOS selection(s) made so far and restarts that phase; `back` while picking a branch's trainings returns to the branch menu with the "selected so far" count unchanged; and a plain single-MOS-plus-one-training run (no navigation keywords used) still completes and exports a report identically to before this change. This is pure `input()`-driven interactive logic, so (like the rest of `cli.py`) it isn't covered by the pytest suite; the full 63-test suite was re-run after these changes and still passes.

**Files changed:** `exceptions.py`, `cli.py`, `main.py`

---

## [25] 2026-09-05 — Support entering more than one MOS

**Why:** per William's direction -- some veterans hold more than one MOS by the time they leave service (e.g. after reclassification to a different job), and the app only ever let a user pick one MOS and one skill level.

- `CreditEvaluator.build_credit_profile()` (`services/credit_evaluator.py`) now takes a sequence of `(mos_code, skill_level)` pairs instead of a single pair; it loops over all of them into the same existing per-course dedup logic, so overlapping courses granted by more than one MOS merge exactly the way overlapping MOS/training courses already did (higher credit value kept, every source recorded, never summed).
- Added `cli.prompt_mos_selections()`: loops "pick an MOS, pick its skill level, ask whether to add another" (mirrors the existing branch-first training loop), accumulating selections; an exact duplicate `(mos_code, skill_level)` re-entry is skipped rather than added twice.
- `main.py` and `ReportGenerator.build_report_text()` updated to carry the full list of MOS selections through end to end; the exported report's "YOUR SELECTIONS" section now lists one line per MOS, and the report filename includes every selected MOS code (e.g. `recommendation_report_12P-25B_<timestamp>.txt`).
- `tests/test_credit_evaluator.py`: updated all 6 existing calls for the new signature and added a new test using two genuinely different MOS codes at different skill levels (an earlier draft of this test mistakenly used the same MOS code at two skill levels, which William caught -- it didn't actually exercise the multi-MOS case).

Verified via the full test suite (63 passed) and by running the real CLI end to end with two different MOS codes (12P skill level 30, 25B skill level 40): confirmed the credit profile correctly merges courses from both (including a real overlap, COM120, contributed by both), the exported report lists both MOS lines, and the filename includes both codes.

**Files changed:** `services/credit_evaluator.py`, `cli.py`, `main.py`, `reports/report_generator.py`, `tests/test_credit_evaluator.py`

---

## [24] 2026-09-05 — Split main.py into pipeline.py, cli.py, and a thin entry point

**Why:** William asked me to pick from three "thin spot" improvements I'd identified and said to do all three ("do all 3 please there is not reason oyucnat"); this is the structural one. `main.py` had grown to hold first-run/refresh detection, all three importers' orchestration, validation, the entire interactive prompt flow, and report export/console display in one file, mixing pipeline concerns with CLI concerns.

- Extracted `pipeline.py`: `needs_conversion()` (renamed from `_needs_conversion`, now public since it's called cross-module), `convert()`, `load()`, `validate_and_report()`, `print_summary()`, and every module-level path constant (`SOURCE_DATA_DIR`, `NORMALIZED_DATA_DIR`, `CONVERSION_ISSUES_DIR`, the three source/CSV paths, `MANIFEST_PATH`).
- Extracted `cli.py`: `print_columns()`, `prompt_mos_selection()`, `prompt_skill_level()`, `prompt_training_selection()`, `print_credit_profile()`, `print_recommendations()` -- all the `input()`/`print()`-driven interactive logic, previously private (`_`-prefixed) functions in `main.py`.
- Rewrote `main.py` down to argument parsing (`--refresh`), logging setup, and the top-level `main()` sequencing that calls into `pipeline` and `cli`.
- Updated `tests/test_refresh_logic.py` to target `pipeline.needs_conversion` and monkeypatch `pipeline`'s module constants, since it previously tested `main._needs_conversion` directly and that function no longer lives there.

Verified by running the full test suite after the split (`pytest tests/`: 62 passed, no failures) and an end-to-end CLI smoke test via piped stdin (MOS 12P, skill level 30, no trainings selected), confirming the credit profile, ranked recommendations, and exported report file are produced the same way as before the split; also re-ran with `--refresh` to confirm source conversion, validation, and the summary printout still work through the new `pipeline` module.

**Files changed:** `main.py`, `pipeline.py` (new), `cli.py` (new), `tests/test_refresh_logic.py`

---

## [23] 2026-09-05 — Deepen ConversionValidator; fix a silent pick-group credit bug it surfaced

**Why:** the third of the three approved "thin spot" options -- checking whether the validator catches structural problems specific to the pick-group capping and program-total logic added in [17], not just the generic field-level checks it already had. Running the new checks against the real (reduced) source data surfaced a genuine bug, not just a documentation gap.

- Added two checks to `services/conversion_validator.py`: a `major_choice`/`general_education_choice` requirement with no `choice_group_target_credits` is now an `error` (the [17] pick-group cap can't apply without it, risking double-counted credit); a program with no detected `program_total_credits` is now a `warning`, reported once per program rather than once per row.
- Running the new check against the real program workbook immediately found 659 real requirement records missing `choice_group_target_credits`. Root-caused and fixed in `importers/program_workbook_importer.py` across three real row patterns, verified by rerunning against the full real data after each fix:
  - A subgroup's label and its `"> Take N credits"` instruction sometimes land on physically different rows (deep column-based indentation splits them across a row boundary) -- the parser only looked in a small window after the label match on the same row. Now searches the whole blob for a co-located take-value, and separately emits independent "take" events so a cross-row continuation is still found. (659 -> 358)
  - When the take-instruction's `>` character sits at an earlier blob position than its own subgroup label (an artifact of how fragments get concatenated), position-ordered event dispatch was resetting the value to `None` right after setting it. Removed the reset-then-update pattern entirely -- the subgroup event now computes and sets its own target directly. (358 -> 205)
  - Some instructions read like `"Take 2 8 credits"` (a stray count number before the real total) -- the intervening-token pattern only skipped letter-words, not numbers. Relaxed it to skip any non-space token, always capturing the number immediately before "credit(s)". (205 -> 0)
- Added two regression tests to `tests/test_program_workbook_importer.py` covering the cross-row and stray-number cases directly, and three new tests to `tests/test_conversion_validator.py` for the new checks.

Verified: 0 validation issues (warnings or errors) against the full real source data after all three fixes, confirmed by a fresh `--refresh` run; the full 128-combination MOS/skill-level/training sweep from [17] re-run clean; and direct inspection confirming previously-broken pick groups (HUM/FINE Arts, SOC/BEHAV) now correctly cap at their true 3-credit target each rather than summing past it.

**Files changed:** `services/conversion_validator.py`, `importers/program_workbook_importer.py`, `tests/test_conversion_validator.py`, `tests/test_program_workbook_importer.py`, `normalized_data/program_requirements.csv`

---

## [22] 2026-09-05 — Add DocxParsingError, MissingProgramTotalError, ReportExportError

**Why:** the first of three approved "thin spot" options -- three failure paths were using a generic or borrowed exception, or none at all, contrary to the spec's custom-exception requirement: the training docx importer reused `WorksheetStructureError` (an xlsx-specific name) for its own docx-structure failures, a program with no detected total credits had no dedicated exception, and `ReportGenerator.export()`'s file write had no error handling at all.

- Added `DocxParsingError(SourceConversionError)` and switched `importers/training_docx_importer.py` to raise/catch it instead of the borrowed `WorksheetStructureError`.
- Added `MissingProgramTotalError(SourceConversionError)`; `importers/program_workbook_importer.py` now raises it per program code missing a total at the end of `import_workbook()` and catches it immediately, turning it into a `ProgramWorkbookIssue` (`source_row=-1`) rather than failing the whole conversion.
- Added `ReportExportError`; `ReportGenerator.export()` now wraps its `Path.write_text()` call and raises it with the underlying `OSError` chained, instead of letting a write failure propagate as a raw `OSError`.
- Considered and deliberately did not add an `InvalidCourseIdError`: `normalize_course_id()` never actually rejects input (it always returns a normalized string), so a dedicated exception for it would be unused dead code, not a real gap.

Verified via the existing test suite: `test_choice_group_id_and_target_shared_across_options` and `test_unsupported_nested_rule_flagged_manual_review_not_guessed` (`tests/test_program_workbook_importer.py`) both use fixtures with no total-credits footer row, and both still pass without crashing -- confirming `MissingProgramTotalError` is caught into a `ProgramWorkbookIssue` rather than propagating. The `DocxParsingError` and `ReportExportError` paths are exercised indirectly by the existing importer/report test coverage; no new tests were added specifically for the exception rename/additions since the underlying behavior didn't change, only which exception type is raised.

**Files changed:** `exceptions.py`, `importers/training_docx_importer.py`, `importers/program_workbook_importer.py`, `reports/report_generator.py`

---

## [21] 2026-09-05 — Add the test suite (57 tests)

**Why:** the spec requires at least 20 meaningful tests across MOS/training/program importers, normalization, validation, refresh logic, evaluation, and ranking, using small test fixtures created for testing rather than depending only on the full supplied files. `tests/` held nothing but an empty `__init__.py` until now.

- Added `tests/conftest.py`: three fixture builders (`build_mos_workbook`, `build_training_docx`, `build_program_workbook`) that construct tiny xlsx/docx files at test time using openpyxl/python-docx, per William's direction -- nothing binary is committed to the repo; every fixture's exact content is visible as plain Python in the test files themselves.
- `tests/test_mos_workbook_importer.py` (5): sheet discovery regardless of name, title detection with/without the leading accessibility row, skill-level column mapping, blank-vs-zero-credit handling, and a malformed sheet being reported rather than crashing the run.
- `tests/test_training_docx_importer.py` (5): branch-heading detection, multiple courses in one equivalency cell, the ampersand separator, narrative paragraphs outside tables being ignored, and combined/ambiguous hours being left unresolved rather than invented.
- `tests/test_program_workbook_importer.py` (5): program boundaries separating distinct programs, a repeated page header neither resetting the program nor losing a total appended to it, course extraction via both the structured-column and flattened-text paths, a Pick group's `choice_group_id`/target being shared correctly across its options, and an unsupported nested rule (`"1 of 2 Groups"`) being flagged `manual_review` rather than guessed.
- `tests/test_normalizer.py` (17, several parametrized): course ID variants collapsing to the same canonical form, whitespace/punctuation normalization, credits/hours numeric coercion, equivalency-cell splitting, and course-ID format validation.
- `tests/test_conversion_validator.py` (7): missing required fields, duplicate MOS/skill/course keys, an unresolved-credit training record correctly excused by its own status vs. one that isn't, bad course-ID format, a program record with no known title, and a fully clean set producing zero issues.
- `tests/test_refresh_logic.py` (5): missing normalized output, no manifest at all (first run), unchanged source, changed source (naming the file), and `--refresh` forcing conversion regardless. Tests `main._needs_conversion` directly, with its module-level path constants monkeypatched to `tmp_path` fixtures rather than touching the real project's `source_data`/`normalized_data`.
- `tests/test_credit_evaluator.py` (6): MOS and training equivalencies evaluated independently by selection, source lineage preserved per entry, a course held from multiple sources deduplicating to one entry, that entry keeping the higher credit value rather than summing, correct total across distinct courses, and zero-credit records excluded.
- `tests/test_recommendation_engine.py` (7): weights applied correctly per requirement type, the [17] pick-group capping behavior (re-tested here as a committed regression test, not just the manual verification from that session), `major_required` matches never capped, descending-score sorting, the full major-required-credits tie-break, zero-match programs excluded outright, and the top-3 limit enforced.

Verified by running the full suite together (`pytest tests/`): all 57 pass with no cross-test interference, in under a second; confirmed `git status` shows only the 9 new test files added, nothing else in the working tree touched by running them.

**Files changed:** `tests/conftest.py`, `tests/test_mos_workbook_importer.py`, `tests/test_training_docx_importer.py`, `tests/test_program_workbook_importer.py`, `tests/test_normalizer.py`, `tests/test_conversion_validator.py`, `tests/test_refresh_logic.py`, `tests/test_credit_evaluator.py`, `tests/test_recommendation_engine.py`, `requirements.txt`, `README.md`

---

## [20] 2026-09-05 — Multi-column layout for the per-branch training list

**Why:** per William's direction, the per-branch training list (up to 87 entries for ARMY) needed to show in multiple columns instead of one long single-column list, so more of it is visible at once without scrolling.

- Added `_print_columns()` to `main.py`: prints a numbered list as a column-major grid (fills top-to-bottom within a column, then wraps to the next column right), using the real terminal width (`shutil.get_terminal_size()`, falling back to 100 columns when not attached to a real terminal). Column width is capped at 46 characters rather than sized to the single longest entry -- checked the actual data first: ARMY's 87 entries have a median length of 33 characters and only 8 exceed 45, so sizing every column to fit the single longest one (62 characters, one outlier) would have forced the whole list down to one column for no real benefit. The rare long entry just spills slightly into the next column's space on its own row instead.
- Wired into `_prompt_training_selection()`'s per-branch training display, replacing the one-item-per-line loop.

Verified by running the real ARMY list (87 entries, now 44 rows across 2 columns instead of 87 rows in 1) at an explicit 120-column width and again with no terminal attached (fallback width), confirming both render the same layout; checked a short branch (NATIONAL GUARD, 4 entries) splits cleanly into 2x2 rather than looking awkward; and re-ran a full MOS/skill-level/training selection end to end to confirm no regressions elsewhere in the flow.

**Files changed:** `main.py`

---

## [19] 2026-09-05 — Redesign the exported recommendation report format

**Why:** per William's direction, the exported report needed a real visual format (section dividers, aligned tables, wrapped paragraphs) rather than a flat text dump -- the previous version ran the match explanation and the "you also hold X" surplus note together into one dense run-on paragraph and used a raw ISO timestamp.

- Rewrote `ReportGenerator.build_report_text()` (`reports/report_generator.py`): `====`/`----` section dividers (YOUR SELECTIONS, POTENTIAL CREDIT SUMMARY, TOP PROGRAM RECOMMENDATIONS, IMPORTANT NOTICE), an aligned `Course / Credits / Source` table for the credit summary and an aligned matched-courses table per program, a human-readable generated-date format (`September 05, 2026 at 02:59 AM` instead of ISO), and paragraphs wrapped to 80 columns via `textwrap` instead of one unbroken line.
- Extracted the "also holds surplus courses" advisory into a shared `surplus_note()` function, built directly from `ProgramRecommendation.surplus_courses` (already-structured data from the [17] capping fix) rather than a string baked into `RecommendationEngine._explain()` that callers would have had to re-parse to reformat. `_explain()` now returns only the match-summary sentence; `main.py`'s console display and the exported report both call `surplus_note()` themselves, so they stay consistent without duplicating the wording.

Verified by generating a real report from a live run (MOS 68W, no trainings) and reading the actual exported file, sent to William directly for review before committing; re-ran the full 128-combination MOS/skill-level/training sweep with report generation included (0 errors); confirmed console output still shows the surplus note correctly on its own line after the explanation-vs-note split; and reconfirmed the validator still reports 0 issues.

**Files changed:** `reports/report_generator.py`, `services/recommendation_engine.py`, `main.py`

---

## [18] 2026-09-05 — Branch-first menu for training selection

**Why:** per William's direction, the training-selection step should be a menu (pick a branch, then see its trainings) rather than one flat numbered list of all 118 trainings, since that list is expected to keep growing as more branches/schools are added later this semester and a single flat list won't scale.

- Added `list_branches()`, `select_branch()`, and `list_trainings_for_branch()` to `CreditEvaluator` (same pure-logic-only pattern as its other selection methods -- no `input()`/`print()`, so they're directly testable).
- Rewrote `main.py`'s `_prompt_training_selection()`: shows a short numbered list of branches (ARMY, COAST GUARD, MARINES, NATIONAL GUARD, NAVY) plus a "Done" option; picking a branch shows only that branch's trainings for selection; after selecting (or pressing Enter for none), it loops back to the branch menu so the user can pick another branch or finish. Selections accumulate (deduplicated) across as many branches as the user visits.

Verified by running the full interactive flow via piped stdin: selecting one training from ARMY then one from MARINES and confirming both accumulate correctly and both appear by name in the exported report (one contributes real credit, the other legitimately contributes zero since it's an unresolved multi-course training from Phase 3 -- confirmed that's expected behavior, not a bug in the new menu); the immediate-"Done" path (no trainings selected); and invalid branch-menu input (non-numeric and out-of-range) correctly re-prompting rather than crashing.

**Files changed:** `services/credit_evaluator.py`, `main.py`

---

## [17] 2026-09-05 — Fix pick-group credit double-counting; exclude manual_review from scoring

**Why:** William identified that when a veteran holds credit for more than one course satisfying the same "pick one/pick N" program requirement (e.g. an MOS granting both MAT143 and MAT171, which both satisfy Information Technology's single 3-credit math requirement), the recommendation engine was counting every matching course independently and summing their credits/scores -- overstating both figures for a requirement that can only actually be satisfied once (or up to its own stated credit target, for a larger elective pool). Resolving the correct rule took real back-and-forth (see this session's transcript) and research into how real degree-audit systems (DegreeWorks' "best fit" placement, the "bucket" analogy) and transfer-credit evaluation actually handle this, since an initial proposal to cap an individual course's own credit value at the requirement's nominal minimum was wrong and would have silently discarded real credit.

- Added `choice_group_id` and `choice_group_target_credits` to `ProgramRequirement` (`models.py`), and to `importers/program_workbook_importer.py`: the parser already detected a subgroup's `"> Take N credits"` instruction but discarded the number -- it's now captured and stamped onto every course parsed under that subgroup, identifying which specific pick group each course option belongs to and what that group's target credit total is.
- Rewrote `RecommendationEngine._score_program()`: `major_choice`/`general_education_choice` matches are now grouped by `choice_group_id`; within each group, real courses are added at their full, uncapped credit value -- highest value first (the documented tie-break, since which specific course to prefer is genuinely a local policy choice with no universal standard, confirmed by research) -- until the group's target is met or exceeded, then no further courses from that same group are added. `major_required` matches are never grouped or capped, since each is independently needed rather than an alternative to the others.
- Excluded courses aren't discarded from the veteran's record -- they're returned as `surplus_courses` on `ProgramRecommendation` and folded into the recommendation's explanation as "you also hold X, which qualifies for the same requirement but isn't counted since it's already satisfied," including a note to consult an FTCC advisor about which option best fits a 4-year transfer plan, since this app has no per-course transfer-articulation data to decide that automatically.
- Related bug fixed in the same code: a `status=manual_review` row (an unmodeled nested choice structure) could still be scored if its `requirement_type` happened to resolve to a known category, contrary to the spec's instruction not to guess an unsafe classification into the weighted score. `_score_program` now excludes `manual_review` rows outright.

Verified extensively: the real MAT143/MAT171-style overlap (Information Technology's math pick group) now correctly shows 4 matched credits instead of 7, with MAT143 reported as surplus; a 4-way equal-value overlap (CIS110/CIS115/NOS110/WEB110) now correctly counts only 1 course instead of summing all 4; the 3 known `manual_review` rows were confirmed to never contribute to any score even when directly targeted; a sweep of all 8 MOS codes across every available skill level, crossed with 0/1/3/10 selected trainings (128 combinations total), ran with 0 errors and correctly triggered the new cap/surplus logic in 48 of the resulting recommendations; and a genuine, naturally-occurring real-data overlap (MOS 68W skill level 30 granting 4 EMS courses that all satisfy Emergency Medical Science's "MAJ Req BIO Pick" group) was run through the actual CLI end to end and produced the correct capped result with no synthetic data involved.

**Files changed:** `models.py`, `importers/program_workbook_importer.py`, `services/recommendation_engine.py`, `normalized_data/program_requirements.csv`

---

## [16] 2026-09-05 — Rename the exported-report output folder to student_reports

**Why:** per William's instruction, the generated recommendation report files should live in a folder named `student_reports/` rather than `exported_reports/`.

- Renamed the directory (`git mv` on its `.gitkeep`, so it's a tracked rename rather than a delete+add), updated `main.py`'s `STUDENT_REPORTS_DIR` constant and the report-export path, and updated the matching `.gitignore` rule (`student_reports/*.txt`) and `README.md`.

Verified by running the full pipeline and confirming the report file is written to `student_reports/` under the same `recommendation_report_<mos_code>_<timestamp>.txt` naming as before.

**Files changed:** `main.py`, `.gitignore`, `README.md`, `student_reports/.gitkeep` (renamed from `exported_reports/.gitkeep`)

---

## [15] 2026-09-03 — Add application logging

**Why:** the spec requires logging conversion decisions, warnings, errors, record counts, selections, deduplication, ranking, and exports (never sensitive personal information) -- nothing logged anywhere until now.

- Added `_configure_logging()` to `main.py`: a file-only handler (no console output, to keep the interactive UI clean) writing to `logs/app.log`.
- Added log calls at each point the spec names: conversion-vs-load decision and why; per-source record/issue counts during conversion (and each individual issue at `warning` level); validation summary and each individual issue (`warning` or `error` by severity); a fatal conversion failure at `error` level; the user's MOS/skill-level/training-count selection; a `deduplicated course` line whenever the credit profile merges the same course from more than one source; the final ranking (each recommended program's code and score); and the exported report's file path.
- The log deliberately never records anything identifying the person running it -- only MOS/skill-level/training codes, course codes, record counts, and outcomes, none of which are personal information since the app never asks for the veteran's name or any other identifying detail in the first place.
- Added `logs/*.log` to `.gitignore`, alongside the existing `exported_reports/*.txt` rule -- the log grows continuously across every run rather than being one-file-per-run, so it's even more clearly a local runtime artifact than the exported reports are.

Verified by running the full pipeline three ways and reading `logs/app.log` after each: a cached-load run, a forced `--refresh` conversion run, and a run selecting a training whose course overlaps with the MOS-granted credit (confirmed the dedup line fires with both sources named). Also verified the error-logging call in isolation against a raised `SourceFileNotFoundError`, since the fatal-conversion-failure path can't be exercised without touching the real source files.

**Files changed:** `main.py`, `.gitignore`, `README.md`

---

## [14] 2026-09-03 — Implement ReportGenerator and export a recommendation report file

**Why:** the spec's Required Demonstration steps and Deliverables both call for exporting and opening a recommendation report, not just printing to console -- `ReportGenerator` was still an empty stub, and `main.py`'s output only ever went to the terminal.

- Implemented `ReportGenerator` (`reports/report_generator.py`): `build_report_text()` renders the veteran's MOS/skill-level/training selections, the potential-credit summary, and the top-3 program recommendations (matched courses with weights/points, applicable credits, score, match percentage, credits remaining, explanation) as one human-readable text report, closing with the assignment spec's exact "Required Notice" disclaimer text. `export()` writes it to a file.
- Wired into `main.py`: after displaying recommendations, builds and exports the report to `exported_reports/recommendation_report_<mos_code>_<timestamp>.txt` and prints the file path.
- Added `exported_reports/` as a new generated-output directory (`.gitkeep` placeholder, matching `normalized_data/`/`conversion_issues/`/`logs/`). Unlike those directories, its `.txt` files are gitignored -- each run produces a new timestamped file, so committing every one would clutter history; a deliberately chosen sample will be committed separately as its own deliverable later.

Verified by generating a report against real converted data (MOS 25B skill level 30, one training selected) and reading the exported file directly: correctly includes the selected training's name (not just its ID), correctly shows the training-sourced course folded into the potential-credit summary and into a program recommendation it happens to apply to, and matches the console output exactly.

**Files changed:** `reports/report_generator.py`, `main.py`, `.gitignore`, `README.md`, `exported_reports/.gitkeep`

---

## [13] 2026-09-03 — Implement Phase 7 recommendation engine

**Why:** Phase 7 of the assignment spec requires matching a veteran's potential-credit profile against every FTCC program by exact course-code matches, scoring by requirement-type weight, ranking the top 3 with a specific tie-break order, and explaining each match -- the last remaining core pipeline phase.

- Added `RECOMMENDATION_WEIGHTS` to `config.py` (`major_required: 3, major_choice: 2, general_education_choice: 1`), stored separately from the converted program data per the spec's explicit instruction not to merge project-defined weights into source-derived data.
- Implemented `RecommendationEngine` (`services/recommendation_engine.py`). For each program, only exact course-code matches against the veteran's profile count; a course with `requirement_type=unresolved` is never scored (no guessing). When the same course appears under more than one requirement group in a program (e.g. both a direct requirement and, elsewhere, an elective choice), the higher-weighted classification is used rather than whichever occurs first. `applicable_matched_credits` (sum of matched credits) and `recommendation_score` (sum of credits × weight) are kept as separate figures, matching the spec's own worked example exactly (verified: ELC112 5cr×w3 + ISC112 2cr×w2 + COM120 3cr×w1 = 10 matched credits, score 22). Programs with zero exact matches are excluded from ranking entirely, not just deprioritized. Ranking applies the spec's 5-step tie-break in order: more major-required credits matched, then more total matched credits, then more matched courses, then higher match percentage, then alphabetical by program title.
- Added `MatchedCourse` and `ProgramRecommendation` to `models.py`.
- Added the top-3 recommendation display to `main.py`'s interactive flow (matched courses with their weight/points, total matched credits, score, match percentage, estimated credits remaining, and a generated explanation), immediately after the Phase 6 credit-profile summary, closing with the spec's estimate-only disclaimer.

Verified by: matching the spec's own worked example precisely (asserted both figures); running the engine against real converted data with a real MOS profile (25B skill level 30) and confirming Information Technology correctly ranks #1 with a sensible 6-course match; and three targeted synthetic tests confirming a program with only an unresolved-type match is excluded entirely, a course appearing twice in one program correctly keeps its higher-weighted classification, and two programs tied on score are correctly ordered by the major-required-credits tie-break rather than falling through to alphabetical. Also ran the complete interactive flow end-to-end through `main.py` and confirmed its output matches the standalone engine test exactly.

**Files changed:** `config.py`, `models.py`, `services/recommendation_engine.py`, `main.py`, `README.md`

---

## [12] 2026-09-03 — Implement Phase 6 user input and credit profile

**Why:** Phase 6 of the assignment spec requires interactively asking for an MOS code/title, displaying and validating available skill levels, showing a numbered list of trainings for the user to select completed ones from, then combining the resulting MOS and training equivalencies into a deduplicated potential-credit summary that preserves every source contributing to a duplicated course and doesn't claim credit is guaranteed.

- Implemented `CreditEvaluator` (`services/credit_evaluator.py`) as pure selection/matching/combination logic with no `input()`/`print()` calls of its own, so it's directly testable without mocking stdin: `find_mos_matches()` (partial code/title search), `select_mos_code()`, `available_skill_levels()`, `validate_skill_level()`, `list_trainings()`, `select_trainings()` (parses comma-separated numbers), and `build_credit_profile()`.
- `build_credit_profile()` combines the selected MOS/skill-level equivalencies (credits > 0 only) with the selected trainings' equivalencies (resolved credits only, skipping the `credits_unresolved`/`no_equivalency_found` cases) into one profile keyed by course ID. When more than one source grants credit for the same course, every contributing source is preserved in a `sources` string on that one entry and the higher credit value is kept -- the course is never counted twice toward the total.
- Added `CreditProfileEntry` to `models.py` and `InvalidSelectionError` to `exceptions.py` (raised by the evaluator's validation methods on an out-of-range or unparseable selection).
- Added the interactive prompting loop to `main.py` (`_prompt_mos_selection`, `_prompt_skill_level`, `_prompt_training_selection`, `_print_credit_profile`), which catches `InvalidSelectionError` and re-prompts rather than crashing. Runs after conversion/loading on every invocation. The credit-summary notice uses the assignment spec's exact "Required Notice" disclaimer text.

Verified two ways: ran every `CreditEvaluator` method directly against the real normalized data (partial-code and partial-title MOS search, no-match and multi-match cases, skill-level listing/validation, training listing/selection including the invalid-number case, and the course-merge case where both an MOS and a training grant credit for the same course -- confirmed it dedupes to one entry with both sources listed rather than two separate rows). Then ran the full interactive flow end-to-end through `main.py` with piped stdin covering: a clean run, an invalid-then-valid MOS query, an invalid-then-valid skill level, an invalid-then-valid training selection, a multi-match MOS selection, and an empty (no trainings) selection -- all produced the same, correct combined profile as the direct logic test.

**Files changed:** `models.py`, `exceptions.py`, `services/credit_evaluator.py`, `main.py`, `README.md`

---

## [11] 2026-09-03 — Implement Phase 5 conversion validation

**Why:** Phase 5 of the assignment spec requires validating normalized data after conversion, before it's used for recommendations: required fields present, course IDs match the normalized format, credits are numeric/zero/blank/unresolved per schema, MOS/skill-level/course combinations aren't accidentally duplicated, and every program requirement belongs to a known program -- `ConversionValidator` was still an empty stub.

- Implemented `ConversionValidator` (`services/conversion_validator.py`) with per-source checks against all three normalized record types: required identifying fields present; course ID matches the canonical normalized format (added `is_valid_course_id()` to `services/normalizer.py`); credits non-negative; MOS records' (mos_code, skill_level, course_id) combination not duplicated; program records belong to a program with known title/metadata (i.e. a recognized program header); a `warning`-severity check for a training record with no course_id that isn't already explained by `no_equivalency_found` status, and for a program record with `requirement_type=unresolved` that isn't already explained by `manual_review` status -- both are deliberately warnings, not errors, since the record's own status field already documents why.
- Added a `ValidationIssue` dataclass (`severity`, `source`, `identifier`, `message`) to `models.py`.
- Wired validation into `main.py` on both code paths (fresh conversion and loading cached normalized data, since Phase 5 says validate "before using it for recommendations" regardless of which path produced the data), writing results to `conversion_issues/validation_issues.csv` and adding the `Warnings:`/`Errors:` summary lines the spec's example conversion summary shows.

Verified two ways: ran the validator against the real converted data (0 issues across all three sources, consistent with the thorough per-importer verification already done) and, to confirm the validator can actually catch problems rather than trivially passing, ran it against synthetic bad records covering all 10 check categories -- all 10 were caught correctly, with no false positive on the one deliberately-legitimate case (a `no_equivalency_found` training record with a blank course_id).

**Files changed:** `models.py`, `services/normalizer.py`, `services/conversion_validator.py`, `main.py`, `README.md`, `conversion_issues/validation_issues.csv`

---

## [10] 2026-09-03 — Implement Phase 1 first-run/refresh detection

**Why:** Phase 1 of the assignment spec requires the app to detect at startup whether normalized data already exists and is current, rebuild only when source files have actually changed (or normalized output is missing), and load existing normalized data otherwise rather than repeating unnecessary conversion -- `main.py` previously just re-ran all three importers unconditionally on every run.

- Added `compute_file_hash()`, `read_manifest()`/`write_manifest()`, and `read_csv()` to `repositories/normalized_data_repository.py`. Change detection is content-hash (SHA-256) based rather than file-modification-time based, so a file touched without its content changing doesn't trigger a needless reconversion; the hash of each source file is recorded in `normalized_data/.conversion_manifest.json` after a successful conversion. `read_csv()` reconstructs the correct dataclass type (`MOSCourseEquivalency`, `TrainingEquivalency`, or `ProgramRequirement`) from a previously written CSV, using `typing.get_type_hints()` to resolve each field's real type (including the `int | None` / `float | None` optional fields) for correct coercion.
- Rewrote `main.py`: on startup it checks whether all three normalized CSVs exist and their manifest matches the current source-file hashes. If either check fails, it converts and writes a fresh manifest; otherwise it loads the existing CSVs instead of re-running the importers. Added a `--refresh` flag to force reconversion regardless.
- Renamed `exceptions.py`'s `MOSMapError` to `SourceConversionError` -- it's the shared base class for all three importers' exceptions now, not MOS-specific, and the old name was misleading now that `main.py` catches it generically.
- On a conversion failure (a caught `SourceConversionError`), `main.py` now prints a clear error, writes `conversion_issues/fatal_conversion_error.txt`, and exits cleanly instead of a raw traceback.

Verified by directly exercising all the scenarios the spec's "Refresh logic" testing area calls for: first run (normalized output missing) correctly converts; an unchanged run correctly loads without reconverting; a file with its content unchanged but modification time touched correctly does *not* trigger reconversion (confirming the hash-based, not mtime-based, design); a simulated source-file change (via a deliberately wrong manifest hash, so the real source files were never touched) correctly reconverts and names the changed file; `--refresh` correctly forces reconversion even when nothing changed; and a missing source file correctly raises a catchable `SourceConversionError` rather than crashing. Also verified full CSV write-then-read round-trip equality against real importer output for all three record types (224, 257, and 1230 records) before wiring it into `main.py`.

**Files changed:** `exceptions.py`, `repositories/normalized_data_repository.py`, `main.py`, `README.md`, `normalized_data/.conversion_manifest.json`

---

## [9] 2026-09-03 — Implement program-workbook importer and normalization pipeline

**Why:** Phase 4 of the assignment spec requires parsing `2026_POS_Reduced.xlsx` -- a printed, report-style export (not a clean table) of FTCC's 10 Programs of Study -- into normalized requirement records, discovering program/group/choice boundaries rather than assuming fixed rows.

- Added `ProgramWorkbookImporter` (`importers/program_workbook_importer.py`). This source is far messier than the MOS/training sources: label text wraps across multiple columns depending on indentation depth (up to 14 different column-position patterns observed), and several rows flatten an entire course record plus the next section's header into one text cell with no structured columns at all. Rather than trying to reconstruct exact original line breaks -- confirmed genuinely ambiguous for a subset of rows, since neither left- nor right-aligned reconstruction was consistently correct -- the importer concatenates each row's label-column text into one blob and pattern-matches against it (program headers, numbered requirement groups, Pick/Courses subgroup labels, "> Take N credits" instructions, and course lines), processing matches in the order they appear in the text so a course record uses the correct group/subgroup state whether that state was established earlier in the same row or is about to change later in it.
- Course hours use the same "read whichever numeric-typed cells are present, last one is Credits" rule established for the MOS importer, generalized to also recover a bare trailing number from string-typed hour cells (found during testing: a small number of Credits cells hold a string like `'(33.00)\n3.00'` -- a group total sharing the cell with the real per-course credit value -- rather than a clean number).
- Program-level total credits are read from three different places the source uses inconsistently: a standalone negative-int row (Excel's accounting format renders negatives in parentheses), a `(XX.XX)` marker trailing the last course before a program ends, and -- found during testing, for Graphic Design specifically -- a total appended directly to a repeated page-header cell.
- Requirement types are classified into the spec's three defined categories (`major_required`, `major_choice`, `general_education_choice`) based on which numbered group and Pick/Courses subgroup a course falls under; courses under a detected multi-level nested choice structure (e.g. "1 of 2 Groups") are marked `status=manual_review` rather than force-classified, per the spec's explicit allowance to flag ambiguous nested rules instead of guessing.
- Built and verified iteratively in `importers/program_workbook_importer_temp.py` (kept per the project's temp-file convention) before being promoted here. Testing surfaced and fixed three real bugs: (1) the string-typed credits-cell case above, which was silently producing `credits=0`; (2) a page-header row's appended total being dropped because the code returned immediately after matching the header pattern; (3) the group-header regex matching the trailing digit of a decimal total (e.g. the `0` in `"(6.00)"`) as a fake `"N)"` group marker, which had been silently misclassifying every course in the affected programs as `general_education_choice`.
- Added `ProgramRequirement` and `ProgramWorkbookIssue` to `models.py`, and wired the importer into `main.py` alongside the other two.

Verified by running `main.py` and inspecting `normalized_data/program_requirements.csv`: all 10 programs converted, 0 issues, 1230 requirement records, 0 records with `credits=0`, 0 duplicate records, and every program's total credits correctly extracted. Fully hand-traced two programs end-to-end against the raw workbook (Information Technology, 443 records, and Welding Technology, 15 records) and spot-checked two statistically unusual programs (HVAC's 99-course general-education pool, and Industrial Systems Technology having zero `major_choice` records) to confirm both are genuine source-data characteristics, not parsing bugs.

**Files changed:** `models.py`, `importers/program_workbook_importer.py`, `importers/program_workbook_importer_temp.py`, `main.py`, `README.md`, `normalized_data/program_requirements.csv`, `conversion_issues/program_workbook_issues.csv`

---

## [8] 2026-09-03 — Codify README/CHANGELOG update policy; bring README.md current

**Why:** per William's instruction in this session, `README.md` and `CHANGELOG.md` should be updated to reflect the work done and any changes to files/structure every time work happens, not just occasionally.

- Added a rule to `CLAUDE.md`'s "Documentation upkeep" section making this binding for every future session/contributor: every approved change gets a `CHANGELOG.md` entry, and a `README.md` update where it affects what README describes, in the same change.
- Brought `README.md` current, which had gone stale after Phase 2 (MOS importer) and Phase 3 (training importer) work: updated the Status line to list what's actually implemented vs. not yet, expanded the project-structure tree to mark each importer/service/repository file's implementation status individually, and added `requirements.txt` and `CHANGELOG.md` to the documented structure.

**Files changed:** `CLAUDE.md`, `README.md`, `CHANGELOG.md`

---

## [7] 2026-09-03 — Implement training-docx importer and normalization pipeline

**Why:** Phase 3 of the assignment spec (`docs/FTCC_Military_Recommender_Revised_Individual_Project.docx`) requires parsing `Appendix J for website2026 (002).docx`'s branch/training/FTCC-equivalency tables into normalized data, following the MOS importer already built for Phase 2.

- Added `TrainingDocxImporter` (`importers/training_docx_importer.py`), using `python-docx` to walk all 6 tables in the source document. It detects branch-heading rows (e.g. `ARMY`, `COAST GUARD`) and column-header rows by content, and correctly carries the current branch across a table that has neither of its own (table 1 continues Army's list from table 0 with no heading row).
- Extended `services/normalizer.py` with `split_course_ids()` (splits comma/ampersand/line-break-separated equivalency cells into normalized course IDs) and `normalize_hours()`.
- Added `TrainingEquivalency` and `TrainingTableIssue` dataclasses to `models.py`.
- Per the spec's explicit restriction against inventing per-course credit values: when a training row lists exactly one FTCC course, its `Hours` value is used directly as that course's credits; when a row lists multiple courses sharing one combined `Hours` value, `course_credits` is left unresolved (`status=credits_unresolved`, `verification_required=True`) rather than guessing a split.
- `training_alias` is extracted from a trailing parenthetical acronym in the training name (e.g. `"Army Basic Leader Course (BLC)"` → `BLC`); left blank when there isn't one. This is a judgment call (the spec lists the field but doesn't define how to populate it), made per William's direction in this session.
- Updated `main.py` to run this importer alongside the MOS importer and print a combined conversion summary.
- Added `requirements.txt` (`openpyxl`, `python-docx`) so the environment is reproducible, and installed `python-docx` (with its `lxml` dependency) locally — required by the spec for Word-table parsing.

Verified by running `main.py` and inspecting `normalized_data/training_equivalencies.csv`: 0 tables flagged for review, 118 distinct training rows expanded into 257 normalized records. Spot-checked branch continuation into table 1, single-course credit resolution, multi-course unresolved handling, alias extraction, and ampersand-separated course splitting against the source document.

**Files changed:** `models.py`, `services/normalizer.py`, `importers/training_docx_importer.py`, `main.py`, `requirements.txt`, `normalized_data/training_equivalencies.csv`, `conversion_issues/training_table_issues.csv`

---

## [6] 2026-09-03 — Implement MOS workbook importer and normalization pipeline

**Why:** Phase 2 of the assignment spec requires parsing `Army_MOS_Maps_Reduced.xlsx`'s 8 MOS worksheets into normalized data, discovering structure rather than hard-coding rows or sheet names.

- Added `MOSWorkbookImporter` (`importers/mos_workbook_importer.py`), which locates each worksheet's MOS title row and `Course ID` header row by content rather than fixed position (title-row position and presence of footer/accessibility rows vary by sheet), extracts the MOS code via regex regardless of spacing/dash inconsistency in the title text, and skips footer rows (`Total Hours Required...`, `End of Worksheet`) by content match.
- Added `normalize_course_id()`, `normalize_text()`, and `normalize_credits()` to `services/normalizer.py`; course IDs like `ELC 117` and `COM 120` normalize to the same canonical form as their no-space equivalents (`ELC117`, `COM120`), matching the inconsistent formatting called out in the spec.
- Added `MOSCourseEquivalency` and `WorksheetIssue` dataclasses to `models.py`, and `SourceFileNotFoundError`/`WorksheetStructureError` custom exceptions to `exceptions.py`.
- Per William's decision in this session: blank or zero skill-level cells are kept as explicit `credits=0, status=no_credit` rows rather than omitted, so "no credit at this level" stays visible, auditable data instead of a silent gap.
- Added `NormalizedDataRepository.write_csv()` (`repositories/normalized_data_repository.py`) to write any list of dataclass records to CSV.
- Added `main.py` to run the importer and print a conversion summary.
- Added `__pycache__/` and `*.pyc` to `.gitignore`, needed once the app actually started running and generating bytecode caches.

Verified by running `main.py`: all 8 worksheets converted with 0 issues, 224 normalized records written (matches the expected 8-sheet × course × 4-skill-level total exactly). Spot-checked course ID normalization and zero/blank-credit handling against the raw workbook contents.

**Files changed:** `models.py`, `exceptions.py`, `services/normalizer.py`, `importers/mos_workbook_importer.py`, `repositories/normalized_data_repository.py`, `main.py`, `.gitignore`, `normalized_data/mos_equivalencies.csv`, `conversion_issues/mos_worksheet_issues.csv`

---

## [5] 2026-09-03 — Scaffold modular project structure

**Why:** William asked for the supplied docs/background files to be moved out of the repo root and for the Python code to be organized modularly, rather than everything sitting flat in root.

- Moved the 3 assignment-brief/rubric/background files into `docs/`, and the 3 runtime source files into `source_data/` (via `git mv`, preserving file history).
- Created the modular package layout defined in the assignment spec's own "Required Architecture" and "Suggested Project Structure" sections: `importers/`, `services/`, `repositories/`, `reports/`, `tests/` packages, plus top-level `main.py`, `config.py`, `models.py`, `exceptions.py` stubs (docstring only, naming each component's responsibility — no logic yet).
- Created empty `normalized_data/`, `conversion_issues/`, `logs/` output directories with `.gitkeep` placeholders.
- Added root `README.md` documenting the structure and the project's constraints (CLI only, no GUI/database, source files must not be modified by the application).

**Files changed:** `README.md`, `main.py`, `config.py`, `models.py`, `exceptions.py`, `importers/__init__.py`, `importers/mos_workbook_importer.py`, `importers/training_docx_importer.py`, `importers/program_workbook_importer.py`, `services/__init__.py`, `services/normalizer.py`, `services/conversion_validator.py`, `services/credit_evaluator.py`, `services/recommendation_engine.py`, `repositories/__init__.py`, `repositories/normalized_data_repository.py`, `reports/__init__.py`, `reports/report_generator.py`, `tests/__init__.py`, `normalized_data/.gitkeep`, `conversion_issues/.gitkeep`, `logs/.gitkeep`, and renames of the 6 supplied files into `docs/`/`source_data/`

---

## [4] 2026-09-03 — Push initial commit to new GitHub repository

**Why:** William wanted the project hosted on GitHub going forward under `adv_python_project_fa26`, as its own dedicated repository rather than the accidental home-directory-wide one.

- William created an empty public repository at `github.com/BECKHAMW3233/adv_python_project_fa26` (no README/license/gitignore initialized there, so the first push would be clean with no history to reconcile).
- Added `.gitignore` scoped to the `_test`/`_temp` scratch-file naming convention already defined in `CLAUDE.md`.
- Committed the 7 files already on disk (the 6 supplied files plus `CLAUDE.md`) and pushed to `origin/main`.

**Files changed:** `.gitignore`; initial commit of `2026_POS_Reduced.xlsx`, `Appendix J for website2026 (002).docx`, `Army_MOS_Maps_Reduced.xlsx`, `CLAUDE.md`, `FTCC_Military_Recommender_Revised_Individual_Project.docx`, `Rubrics CSC221_M2Pro2.docx`, `Understanding Military MOS Codes & College Credit.pdf`

---

## [3] 2026-09-03 — Scope git to the project folder

**Why:** the git repository rooted at `C:\Users\willb` spanned William's entire home directory (a known issue already flagged in `CLAUDE.md`), so `git status` from the project folder showed unrelated personal files. William asked for this folder to have its own `.git` so history would be ready to carry over to GitHub later.

- Ran `git init` inside `Adv_Python_Project`, giving it its own independent repository, nested inside but separate from the home-directory repo.

**Files changed:** none tracked (repository initialization only)

---

## [2] 2026-09-03 — Update CLAUDE.md concept section to reflect the real assignment spec

**Why:** the project folder gained real assignment files (the FTCC Military Recommender spec, grading rubric, and source data), making `CLAUDE.md`'s original vague "college VP" concept description stale and far less detailed than what was now actually known.

- Replaced the "Project status" / "General concept" section with a summary grounded in `FTCC_Military_Recommender_Revised_Individual_Project.docx`: what the CLI application does, the three supplied source files, and the required pipeline stages.
- Noted that whether this individual assignment becomes the foundation of the later group project is still undecided, per William's answer when asked.

**Files changed:** `CLAUDE.md`

---

## [1] 2026-09-03 — Project files added: assignment spec, source data, and background reading

**Why:** the project moved from an empty, concept-only folder to having real assignment materials to work from.

- William added 7 files to the project folder: the CSC221 Advanced Python individual-project assignment brief (`FTCC_Military_Recommender_Revised_Individual_Project.docx`), the course grading rubric (`Rubrics CSC221_M2Pro2.docx`), background reading on military MOS codes and college credit, and the 3 source data files the application must ingest (`Army_MOS_Maps_Reduced.xlsx`, `Appendix J for website2026 (002).docx`, `2026_POS_Reduced.xlsx`).

**Files changed:** `2026_POS_Reduced.xlsx`, `Appendix J for website2026 (002).docx`, `Army_MOS_Maps_Reduced.xlsx`, `FTCC_Military_Recommender_Revised_Individual_Project.docx`, `Rubrics CSC221_M2Pro2.docx`, `Understanding Military MOS Codes & College Credit.pdf` (added to the folder before git was initialized)
