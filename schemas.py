from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

# User Schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str
    department: str
    manager_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None

# Achievement Schemas
class AchievementBase(BaseModel):
    quarter: str
    planned_value: Optional[float] = None
    actual_value: Optional[float] = None
    actual_date: Optional[date] = None
    status: Optional[str] = "not_started"

class AchievementCreate(AchievementBase):
    goal_id: int

class AchievementResponse(AchievementBase):
    id: int
    goal_id: int
    updated_at: datetime

    class Config:
        from_attributes = True

# Goal Schemas
class GoalBase(BaseModel):
    thrust_area: str
    title: str
    description: str
    uom_type: str
    target_value: Optional[float] = None
    target_date: Optional[date] = None
    weightage: float

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    target_value: Optional[float] = None
    weightage: Optional[float] = None

class GoalResponse(GoalBase):
    id: int
    goal_sheet_id: int
    is_shared: bool
    shared_from_goal_id: Optional[int] = None
    status: str
    achievements: List[AchievementResponse] = []

    class Config:
        from_attributes = True

# GoalSheet Schemas
class GoalSheetBase(BaseModel):
    cycle_year: int

class GoalSheetResponse(GoalSheetBase):
    id: int
    employee_id: int
    status: str
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    goals: List[GoalResponse] = []

    class Config:
        from_attributes = True

# Cycle Config
class CycleConfigBase(BaseModel):
    cycle_year: int
    goal_setting_open: date
    q1_open: date
    q2_open: date
    q3_open: date
    q4_open: date
    is_active: bool = True

class CycleConfigResponse(CycleConfigBase):
    id: int

    class Config:
        from_attributes = True

# Checkin Comment
class CheckinCommentCreate(BaseModel):
    goal_sheet_id: int
    quarter: str
    comment: str

class CheckinCommentResponse(BaseModel):
    id: int
    goal_sheet_id: int
    manager_id: int
    quarter: str
    comment: str
    created_at: datetime

    class Config:
        from_attributes = True
