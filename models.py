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
