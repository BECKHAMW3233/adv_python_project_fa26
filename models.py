"""Normalized-record schema / data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MOSCourseEquivalency:
    mos_code: str
    mos_title: str
    branch: str
    skill_level: str
    course_id: str
    course_title: str
    credits: int
    course_level: str
    source_file: str
    source_sheet: str
    status: str
    notes: str


@dataclass
class WorksheetIssue:
    source_file: str
    source_sheet: str
    message: str


@dataclass
class TrainingEquivalency:
    training_id: str
    branch: str
    training_name: str
    training_alias: str
    course_id: str
    course_credits: int | None
    source_total_hours: int | None
    verification_required: bool
    condition: str
    source_file: str
    source_table: str
    status: str
    notes: str


@dataclass
class TrainingTableIssue:
    source_file: str
    source_table: str
    message: str


@dataclass
class ProgramRequirement:
    program_code: str
    program_title: str
    credential_type: str
    catalog_year: str
    program_total_credits: float | None
    requirement_group: str
    requirement_type: str
    course_id: str
    course_credits: int
    source_file: str
    source_row: int
    raw_rule_text: str
    status: str
    notes: str


@dataclass
class ProgramWorkbookIssue:
    source_file: str
    source_row: int
    message: str


@dataclass
class ValidationIssue:
    severity: str  # "warning" | "error"
    source: str  # "mos" | "training" | "program"
    identifier: str
    message: str
