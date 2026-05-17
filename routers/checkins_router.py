from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas, auth
from database import get_db
from datetime import datetime

router = APIRouter(prefix="/checkins", tags=["checkins"])

@router.get("/{sheet_id}")
def get_checkins(sheet_id: int, quarter: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404)
        
    goals = db.query(models.Goal).filter(models.Goal.goal_sheet_id == sheet.id).all()
    goal_ids = [g.id for g in goals]
    achievements = db.query(models.Achievement).filter(models.Achievement.goal_id.in_(goal_ids), models.Achievement.quarter == quarter).all()
    return achievements

@router.put("/achievement/{goal_id}")
def log_achievement(goal_id: int, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404)
        
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.id == goal.goal_sheet_id).first()
    if sheet.status != 'approved':
        raise HTTPException(status_code=400, detail="Sheet must be approved to log achievements")
        
    ach = db.query(models.Achievement).filter(models.Achievement.goal_id == goal_id, models.Achievement.quarter == payload["quarter"]).first()
    if not ach:
        ach = models.Achievement(goal_id=goal_id, quarter=payload["quarter"])
        db.add(ach)
        
    if "actual_value" in payload:
        ach.actual_value = payload["actual_value"]
    if "actual_date" in payload:
        ach.actual_date = datetime.strptime(payload["actual_date"], "%Y-%m-%d").date() if payload["actual_date"] else None
    if "status" in payload:
        ach.status = payload["status"]
        
    ach.updated_at = datetime.utcnow()
    db.commit()
    return ach

@router.post("/comment")
def add_comment(payload: schemas.CheckinCommentCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role not in ['manager', 'admin']:
        raise HTTPException(status_code=403)
        
    cmt = models.CheckinComment(**payload.model_dump(), manager_id=current_user.id)
    db.add(cmt)
    db.commit()
    return cmt

@router.get("/manager/team")
def get_team_checkins(quarter: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role not in ['manager', 'admin']:
        raise HTTPException(status_code=403)
        
    reports = db.query(models.User).filter(models.User.manager_id == current_user.id).all()
    emp_ids = [r.id for r in reports]
    
    sheets = db.query(models.GoalSheet).filter(models.GoalSheet.employee_id.in_(emp_ids)).all()
    sheet_ids = [s.id for s in sheets]
    
    goals = db.query(models.Goal).filter(models.Goal.goal_sheet_id.in_(sheet_ids)).all()
    goal_ids = [g.id for g in goals]
    
    achievements = db.query(models.Achievement).filter(models.Achievement.goal_id.in_(goal_ids), models.Achievement.quarter == quarter).all()
    return achievements
