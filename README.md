# adv_python_project_fa26

**FTCC Military Credit and Program Recommender** -- a command-line Python application (CSC221 Advanced Python individual project) that reads Fayetteville Technical Community College's supplied MOS, military-training-equivalency, and program-of-study source files and recommends FTCC degree programs based on a veteran's military background.

Full assignment spec: [`docs/FTCC_Military_Recommender_Revised_Individual_Project.docx`](docs/FTCC_Military_Recommender_Revised_Individual_Project.docx). Full history of work on this project: [`CHANGELOG.md`](CHANGELOG.md).

**Status:** in progress. Implemented so far: the three source importers (Phases 2-4), first-run/refresh detection (Phase 1), and schema/integrity validation (Phase 5). Not yet implemented: user input / credit evaluation (Phase 6), recommendation ranking (Phase 7), and the test suite.

## Usage

```
python main.py             Convert (if source files are new/changed) and print a summary,
                            or load existing normalized data if it's already current
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
                        three importers, loads existing normalized data when it's current
config.py              Recommendation weights and other settings (not yet populated)
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
  credit_evaluator.py            Not yet implemented
  recommendation_engine.py       Not yet implemented
repositories/           Read/write normalized CSV/JSON data
  normalized_data_repository.py  Implemented -- CSV read/write, source-file hashing, refresh manifest
reports/                Console and exported reports (not yet implemented)
tests/                  Test suite (not yet started)
normalized_data/        Generated normalized output -- mos_equivalencies.csv, training_equivalencies.csv,
                         program_requirements.csv, .conversion_manifest.json (refresh-detection record)
conversion_issues/      Generated parsing-issue reports -- currently empty for all sources and for
                         validation (no issues found)
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
