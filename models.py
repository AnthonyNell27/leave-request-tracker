from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum
from database import Base
import enum


class LeaveType(str, enum.Enum):
    VACATION = "Vacation"
    SICK = "Sick"
    EMERGENCY = "Emergency"


class LeaveStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    leave_type = Column(Enum(LeaveType), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    reason = Column(String, nullable=True)

    status = Column(
        Enum(LeaveStatus),
        nullable=False,
        default=LeaveStatus.DRAFT
    )