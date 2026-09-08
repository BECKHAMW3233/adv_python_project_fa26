# adv_python_project_fa26

**FTCC Military Credit and Program Recommender** -- a command-line Python application (CSC221 Advanced Python individual project) that reads Fayetteville Technical Community College's supplied MOS, military-training-equivalency, and program-of-study source files and recommends FTCC degree programs based on a veteran's military background.

Full assignment spec: [docs/FTCC_Military_Recommender_Revised_Individual_Project.docx](docs/FTCC_Military_Recommender_Revised_Individual_Project.docx). Full history of work on this project: [CHANGELOG.md](CHANGELOG.md). Full usage walkthrough (including what a "skill level" prompt is actually asking for): [INSTRUCTIONS.md](INSTRUCTIONS.md).

**Status:** in progress. The full pipeline (Phases 1-7) is implemented and runnable end to end, including an exported recommendation report file, an application log written on every run, and a 72-test suite covering every area the spec's Testing Requirements table lists. main.py is a thin entry point over pipeline.py (conversion/load/validation) and cli.py (interactive prompts/console display), and ConversionValidator checks pick-group and program-total structural gaps in addition to field-level issues. A user can enter more than one MOS (a veteran may hold more than one by the time they leave service), and every interactive prompt accepts back/exit to correct an earlier answer or quit immediately. A training row that names a course without its own credit value (a combined-hours block covering several courses) is now resolved against a confirmed course-credit reference (the FTCC catalog, or another training row that already resolved the same course) rather than left silently blank; every course shown in the console or exported report includes its real title, not just its code. The full pipeline was verified end-to-end against the real supplied source data on 2026-09-08 (full test suite, a forced --refresh reconversion, an exhaustive MOS/training combination sweep, and manual CLI runs) -- see CHANGELOG entry 33. Not yet implemented: the flowchart, reflection document, full schema/ranking-formula README section, and a deliberately committed sample report.

## Usage

```
python main.py             Convert (if source files are new/changed) and print a summary,
                            or load existing normalized data if it's already current --
                            then interactively prompt for one or more MOS codes (and each
                            one's skill level), walk a branch-first menu to select completed
                            trainings (pick a branch, select from its trainings shown in a
                            multi-column list sized to your terminal width, repeat or
                            finish), and print a potential-credit summary plus the top 3
                            recommended FTCC programs. Every prompt accepts 'back' (return
                            to the previous step) or 'exit' (quit immediately, no report)
                            in place of a normal answer.
python main.py --refresh   Force reconversion from source files regardless of whether
                            normalized data looks current
python -m pytest tests/    Run the test suite (72 tests; requires pytest, in requirements.txt)
```

Change detection is content-hash based (not file-modification-time based), recorded in normalized_data/.conversion_manifest.json after each conversion.

## Project structure

```
docs/                 Assignment brief, grading rubric, background reading
source_data/          Unmodified files supplied for the project -- MOS workbook,
                       training-equivalency doc, FTCC programs-of-study workbook
main.py                Entry point -- argument parsing (--refresh), logging setup, and the
                        top-level sequencing that wires pipeline.py and cli.py together
pipeline.py             First-run/refresh detection (Phase 1), source conversion via the three
                        importers, loading existing normalized data, and validation
cli.py                  Interactive MOS/skill-level/training prompt flow (Phase 6, supports
                        entering more than one MOS) and console display of the credit
                        profile and ranked recommendations (Phase 7); every prompt accepts
                        'back'/'exit' navigation keywords
config.py              RECOMMENDATION_WEIGHTS (major_required=3, major_choice=2,
                        general_education_choice=1) -- project settings, kept separate
                        from the converted FTCC program data per the assignment spec
models.py              Normalized-record schema / data models
exceptions.py          Custom exceptions
importers/             Source-specific parsers
  mos_workbook_importer.py       Implemented -- parses all 8 MOS worksheets
  training_docx_importer.py      Implemented -- parses the 6 branch equivalency tables
  program_workbook_importer.py   Implemented -- parses all 10 FTCC programs' requirement rules,
                                  including each course's real title (not just its code)
services/              Normalization, validation, credit evaluation, recommendation ranking
  normalizer.py                  Implemented -- course ID / text / credits / hours normalization
  conversion_validator.py        Implemented -- required fields, course ID format, duplicate
                                  (MOS/skill level/course) detection, unresolved requirement_type,
                                  choice-type requirements missing a pick-group credit target,
                                  programs missing a detected total credit count
  credit_evaluator.py            Implemented -- MOS/training matching, branch-menu training
                                  listing, selection validation, deduplicated potential-credit
                                  profile with source lineage and course titles (an MOS
                                  record's own title, or the FTCC catalog's for a
                                  training-sourced course)
  recommendation_engine.py       Implemented -- exact course-code matching, weighted scoring,
                                  pick-group credit capping (a course only counts toward a
                                  requirement's real target, never summed past what's needed
                                  across alternatives), top-3 ranking with tie-breaks, match %,
                                  and explanations
  course_credit_resolver.py      Implemented -- resolves a training row that named a course
                                  without its own credit value (a combined-hours block
                                  covering several courses) against a confirmed reference
                                  (the FTCC catalog, or another training row that already
                                  resolved the same course); never guesses a split, and a
                                  course confirmed nowhere stays unresolved
repositories/           Read/write normalized CSV/JSON data
  normalized_data_repository.py  Implemented -- CSV read/write, source-file hashing, refresh manifest
reports/                Console and exported reports
  report_generator.py            Implemented -- formatted report text (section dividers,
                                  aligned tables, wrapped paragraphs, a Title column for every
                                  course) shared by console display and the exported file;
                                  surplus_note() advisory helper
tests/                  72 tests covering every area the spec's Testing Requirements table
                         lists (importers, normalization, validation, refresh logic,
                         evaluation, ranking), plus course-credit-reference and course-title
                         coverage; fixtures are tiny files built at test time (conftest.py),
                         not the full supplied source files
normalized_data/        Generated normalized output -- mos_equivalencies.csv, training_equivalencies.csv,
                         program_requirements.csv, course_credits_reference.csv,
                         .conversion_manifest.json (refresh-detection record)
conversion_issues/      Generated parsing-issue reports -- currently empty for all sources and for
                         validation (no issues found)
student_reports/        Generated per-run recommendation report files (timestamped .txt,
                         gitignored -- regenerated on every run, not canonical output)
logs/                   app.log -- conversion decisions, record counts, warnings/errors,
                         user selections, deduplication, ranking, exports (gitignored,
                         grows across runs; never logs veteran-identifying information)
requirements.txt        Python dependencies (openpyxl, python-docx, pytest)
CHANGELOG.md            Full history of approved changes to this project
INSTRUCTIONS.md         Full CLI usage walkthrough and the skill-level <-> Army rank
                        reference (DA Pam 611-21), for a user of the program
```

## Constraints

- Command-line only -- no GUI, no database, per the assignment's Restrictions.
- Files in source_data/ are supplied source documents and must not be modified by the application.
- Normalized data must be produced by the application from source_data/, never hand-typed.

## Documentation upkeep

README.md and CHANGELOG.md are updated as part of every approved change to this project's files or structure, not as separate follow-ups.
