# adv_python_project_fa26

**FTCC Military Credit and Program Recommender** -- a command-line Python application (CSC221 Advanced Python individual project) that reads Fayetteville Technical Community College's supplied MOS, military-training-equivalency, and program-of-study source files and recommends FTCC degree programs based on a veteran's military background.

Full assignment spec: [`docs/FTCC_Military_Recommender_Revised_Individual_Project.docx`](docs/FTCC_Military_Recommender_Revised_Individual_Project.docx). Full history of work on this project: [`CHANGELOG.md`](CHANGELOG.md).

**Status:** in progress. Implemented so far: the MOS workbook importer (Phase 2) and the training-docx importer (Phase 3), both with working normalization and CSV output. Not yet implemented: the program workbook importer (Phase 4), validation reporting beyond per-source issue lists, user input / credit evaluation (Phase 6), recommendation ranking (Phase 7), and the test suite.

## Project structure

```
docs/                 Assignment brief, grading rubric, background reading
source_data/          Unmodified files supplied for the project -- MOS workbook,
                       training-equivalency doc, FTCC programs-of-study workbook
main.py                Entry point, orchestrates the pipeline (currently: MOS + training import)
config.py              Recommendation weights and other settings (not yet populated)
models.py              Normalized-record schema / data models
exceptions.py          Custom exceptions
importers/             Source-specific parsers
  mos_workbook_importer.py       Implemented -- parses all 8 MOS worksheets
  training_docx_importer.py      Implemented -- parses the 6 branch equivalency tables
  program_workbook_importer.py   Not yet implemented
services/              Normalization, validation, credit evaluation, recommendation ranking
  normalizer.py                  Implemented -- course ID / text / credits / hours normalization
  conversion_validator.py        Not yet implemented
  credit_evaluator.py            Not yet implemented
  recommendation_engine.py       Not yet implemented
repositories/           Read/write normalized CSV/JSON data
  normalized_data_repository.py  Implemented -- writes dataclass records to CSV
reports/                Console and exported reports (not yet implemented)
tests/                  Test suite (not yet started)
normalized_data/        Generated normalized output -- mos_equivalencies.csv, training_equivalencies.csv
conversion_issues/      Generated parsing-issue reports -- currently empty for both sources (no issues found)
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
