"""
Pydantic schemas for the Leave Request Tracker API.

Two kinds of schema live here:
  - *Out* schemas    -> what the API SENDS BACK (responses)
  - *Create* schemas -> what the API ACCEPTS (request bodies)

Keeping them separate is deliberate: the client should only be able to set
the fields it legitimately owns. The server controls everything else.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, computed_field, model_validator

from models import LeaveType, LeaveStatus


class EmployeeOut(BaseModel):
    """Response shape for a single employee (e.g. GET /employees)."""

    id: int
    name: str

    class Config:
        # Lets Pydantic build this schema straight from a SQLAlchemy model
        # object (reading obj.id, obj.name) instead of requiring a dict.
        from_attributes = True


class LeaveRequestOut(BaseModel):
    """
    Response shape for a leave request (GET /leave-requests).

    Includes server-controlled fields the client never sets directly:
      - id     -> assigned by the database
      - status -> set by the server (every request starts as DRAFT)
    """

    id: int
    employee_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None          # optional: may be null
    status: LeaveStatus

    @computed_field      # include this derived value in the output JSON
    @property
    def number_of_days(self) -> int:
        # Span of the leave, measured from start_date to end_date.
        return (self.end_date - self.start_date).days + 1 

    class Config:
        from_attributes = True


class LeaveRequestCreate(BaseModel):
    """
    Request body for creating a leave request (POST /leave-requests).

    Note what's MISSING compared to LeaveRequestOut:
      - no `id`     -> the database generates it
      - no `status` -> the server forces it to DRAFT
    A client can't create an already-APPROVED request, because there's no
    field here for it to set. That omission is the security boundary.
    """

    employee_id: int
    leave_type: LeaveType
    start_date: date
    end_date: date
    reason: Optional[str] = None

    @model_validator(mode="after")
    def check_dates(self):
        # Runs AFTER the fields are parsed into real `date` objects, so the
        # comparisons below are date-vs-date. Raising ValueError here makes
        # FastAPI return a 422 response and the request never hits the DB.
        if self.start_date < date.today():
            raise ValueError("start_date cannot be in the past")
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class LeaveRequestUpdate(BaseModel):
    # PATCH = partial update: every field optional, client sends only
    # what it wants to change. No id/status/employee_id — same trust
    # boundary as Create (status changes are Stage 2's transitions).
    leave_type: Optional[LeaveType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: Optional[str] = None