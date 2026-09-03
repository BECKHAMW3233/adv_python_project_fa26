# Changelog

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
