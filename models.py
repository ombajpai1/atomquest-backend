from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, Date, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String) # employee, manager, admin
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    department = Column(String)
    is_active = Column(Boolean, default=True)

    manager = relationship("User", remote_side=[id])

class GoalSheet(Base):
    __tablename__ = "goal_sheets"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"))
    cycle_year = Column(Integer)
    status = Column(String, default="draft") # draft, submitted, approved, rework
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    employee = relationship("User", foreign_keys=[employee_id])
    approver = relationship("User", foreign_keys=[approved_by])
    goals = relationship("Goal", back_populates="goal_sheet")
    comments = relationship("CheckinComment", back_populates="goal_sheet")

class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    goal_sheet_id = Column(Integer, ForeignKey("goal_sheets.id"))
    thrust_area = Column(String)
    title = Column(String)
    description = Column(String)
    uom_type = Column(String) # min, max, timeline, zero
    target_value = Column(Float, nullable=True)
    target_date = Column(Date, nullable=True)
    weightage = Column(Float)
    is_shared = Column(Boolean, default=False)
    shared_from_goal_id = Column(Integer, ForeignKey("goals.id"), nullable=True)
    status = Column(String, default="not_started") # not_started, on_track, completed

    goal_sheet = relationship("GoalSheet", back_populates="goals")
    achievements = relationship("Achievement", back_populates="goal")

class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    quarter = Column(String) # Q1, Q2, Q3, Q4
    planned_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    actual_date = Column(Date, nullable=True)
    status = Column(String, default="not_started")
    updated_at = Column(DateTime, default=datetime.utcnow)

    goal = relationship("Goal", back_populates="achievements")

class CheckinComment(Base):
    __tablename__ = "checkin_comments"

    id = Column(Integer, primary_key=True, index=True)
    goal_sheet_id = Column(Integer, ForeignKey("goal_sheets.id"))
    manager_id = Column(Integer, ForeignKey("users.id"))
    quarter = Column(String) # Q1, Q2, Q3, Q4
    comment = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    goal_sheet = relationship("GoalSheet", back_populates="comments")
    manager = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    entity_type = Column(String)
    entity_id = Column(Integer)
    old_value = Column(String) # JSON string
    new_value = Column(String) # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow)

class CycleConfig(Base):
    __tablename__ = "cycle_configs"

    id = Column(Integer, primary_key=True, index=True)
    cycle_year = Column(Integer, unique=True)
    goal_setting_open = Column(Date)
    q1_open = Column(Date)
    q2_open = Column(Date)
    q3_open = Column(Date)
    q4_open = Column(Date)
    is_active = Column(Boolean, default=True)

class EscalationAlert(Base):
    __tablename__ = "escalation_alerts"
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String)          # "approval_overdue" | "checkin_missing"
    goal_sheet_id = Column(Integer, ForeignKey("goal_sheets.id"))
    employee_id = Column(Integer, ForeignKey("users.id"))
    escalated_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
