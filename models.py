"""Normalized-record schema / data models."""

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
