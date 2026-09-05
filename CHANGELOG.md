# Changelog

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
