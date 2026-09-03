# adv_python_project_fa26

**FTCC Military Credit and Program Recommender** -- a command-line Python application (CSC221 Advanced Python individual project) that reads Fayetteville Technical Community College's supplied MOS, military-training-equivalency, and program-of-study source files and recommends FTCC degree programs based on a veteran's military background.

Full assignment spec: [`docs/FTCC_Military_Recommender_Revised_Individual_Project.docx`](docs/FTCC_Military_Recommender_Revised_Individual_Project.docx).

**Status:** structure only. Folders and module stubs are scaffolded; no application logic has been written yet.

## Project structure

```
docs/               Assignment brief, grading rubric, background reading
source_data/         Unmodified files supplied for the project -- MOS workbook,
                     training-equivalency doc, FTCC programs-of-study workbook
main.py              Entry point, orchestrates the pipeline
config.py            Recommendation weights and other settings
models.py            Normalized-record schema / data models
exceptions.py        Custom exceptions
importers/           Source-specific parsers (MOS workbook, training docx, program workbook)
services/            Normalization, validation, credit evaluation, recommendation ranking
repositories/        Read/write normalized CSV/JSON data
reports/             Console and exported reports
tests/               Test suite
normalized_data/     Generated normalized output (runtime, currently empty)
conversion_issues/   Generated parsing-issue reports (runtime, currently empty)
logs/                Generated application logs (runtime, currently empty)
```

## Constraints

- Command-line only -- no GUI, no database, per the assignment's Restrictions.
- Files in `source_data/` are supplied source documents and must not be modified by the application.
- Normalized data must be produced by the application from `source_data/`, never hand-typed.
