# adv_python_project_fa26

**FTCC Military Credit and Program Recommender** -- a command-line Python application (CSC221 Advanced Python individual project) that reads Fayetteville Technical Community College's supplied MOS, military-training-equivalency, and program-of-study source files and recommends FTCC degree programs based on a veteran's military background.

Full assignment spec: [`docs/FTCC_Military_Recommender_Revised_Individual_Project.docx`](docs/FTCC_Military_Recommender_Revised_Individual_Project.docx). Full history of work on this project: [`CHANGELOG.md`](CHANGELOG.md).

**Status:** in progress. The full pipeline (Phases 1-7) is implemented and runnable end to end, including an exported recommendation report file written on every run. Not yet implemented: logging and the test suite.

## Usage

```
python main.py             Convert (if source files are new/changed) and print a summary,
                            or load existing normalized data if it's already current --
                            then interactively prompt for an MOS, skill level, and
                            completed trainings, and print a potential-credit summary
                            plus the top 3 recommended FTCC programs
python main.py --refresh   Force reconversion from source files regardless of whether
                            normalized data looks current
```

Change detection is content-hash based (not file-modification-time based), recorded in `normalized_data/.conversion_manifest.json` after each conversion.

## Project structure

```
docs/                 Assignment brief, grading rubric, background reading
source_data/          Unmodified files supplied for the project -- MOS workbook,
                       training-equivalency doc, FTCC programs-of-study workbook
main.py                Entry point -- first-run/refresh detection (Phase 1), orchestrates the
                        three importers or loads existing normalized data, runs the interactive
                        MOS/skill-level/training prompt flow (Phase 6), displays ranked program
                        recommendations (Phase 7), and exports a report file
config.py              RECOMMENDATION_WEIGHTS (major_required=3, major_choice=2,
                        general_education_choice=1) -- project settings, kept separate
                        from the converted FTCC program data per the assignment spec
models.py              Normalized-record schema / data models
exceptions.py          Custom exceptions
importers/             Source-specific parsers
  mos_workbook_importer.py       Implemented -- parses all 8 MOS worksheets
  training_docx_importer.py      Implemented -- parses the 6 branch equivalency tables
  program_workbook_importer.py   Implemented -- parses all 10 FTCC programs' requirement rules
services/              Normalization, validation, credit evaluation, recommendation ranking
  normalizer.py                  Implemented -- course ID / text / credits / hours normalization
  conversion_validator.py        Implemented -- required fields, course ID format, duplicate
                                  (MOS/skill level/course) detection, unresolved requirement_type
  credit_evaluator.py            Implemented -- MOS/training matching, selection validation,
                                  deduplicated potential-credit profile with source lineage
  recommendation_engine.py       Implemented -- exact course-code matching, weighted scoring,
                                  top-3 ranking with tie-breaks, match %, and explanations
repositories/           Read/write normalized CSV/JSON data
  normalized_data_repository.py  Implemented -- CSV read/write, source-file hashing, refresh manifest
reports/                Console and exported reports
  report_generator.py            Implemented -- builds the recommendation report text (also used
                                  for console display) and writes it to an export file
tests/                  Test suite (not yet started)
normalized_data/        Generated normalized output -- mos_equivalencies.csv, training_equivalencies.csv,
                         program_requirements.csv, .conversion_manifest.json (refresh-detection record)
conversion_issues/      Generated parsing-issue reports -- currently empty for all sources and for
                         validation (no issues found)
exported_reports/       Generated per-run recommendation report files (timestamped .txt,
                         gitignored -- regenerated on every run, not canonical output)
logs/                   Generated application logs (runtime, currently empty)
requirements.txt        Python dependencies (openpyxl, python-docx)
CHANGELOG.md            Full history of approved changes to this project
```

## Constraints

- Command-line only -- no GUI, no database, per the assignment's Restrictions.
- Files in `source_data/` are supplied source documents and must not be modified by the application.
- Normalized data must be produced by the application from `source_data/`, never hand-typed.

## Documentation upkeep

`README.md` and `CHANGELOG.md` are updated as part of every approved change to this project's files or structure, not as separate follow-ups.
