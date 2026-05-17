from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
from datetime import datetime

import models, schemas, auth
from database import get_db
from routers.goals_router import log_audit

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=List[schemas.UserResponse])
def get_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403)
    return db.query(models.User).all()

@router.post("/users", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403)
        
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_pwd = auth.get_password_hash(user.password)
    db_user = models.User(
        name=user.name, email=user.email, hashed_password=hashed_pwd,
        role=user.role, manager_id=user.manager_id, department=user.department
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403)
        
    u = db.query(models.User).filter(models.User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404)
        
    for k, v in payload.items():
        if hasattr(u, k):
            if k == 'password':
                setattr(u, 'hashed_password', auth.get_password_hash(v))
            else:
                setattr(u, k, v)
    db.commit()
    return u

@router.get("/cycle", response_model=List[schemas.CycleConfigResponse])
def get_cycle(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.CycleConfig).all()

@router.post("/cycle")
def set_cycle(payload: schemas.CycleConfigBase, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403)
        
    c = db.query(models.CycleConfig).filter(models.CycleConfig.cycle_year == payload.cycle_year).first()
    if c:
        for k, v in payload.model_dump().items():
            setattr(c, k, v)
    else:
        c = models.CycleConfig(**payload.model_dump())
        db.add(c)
    db.commit()
    return c

@router.post("/shared-goals")
def push_shared_goals(payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403)
        
    base_goal = db.query(models.Goal).filter(models.Goal.id == payload["goal_id"]).first()
    if not base_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    emp_ids = payload["employee_ids"]
    for emp_id in emp_ids:
        sheet = db.query(models.GoalSheet).filter(models.GoalSheet.employee_id == emp_id, models.GoalSheet.cycle_year == base_goal.goal_sheet.cycle_year).first()
        if not sheet:
            sheet = models.GoalSheet(employee_id=emp_id, cycle_year=base_goal.goal_sheet.cycle_year)
            db.add(sheet)
            db.commit()
            db.refresh(sheet)
            
        new_g = models.Goal(
            goal_sheet_id=sheet.id, thrust_area=base_goal.thrust_area, title=base_goal.title,
            description=base_goal.description, uom_type=base_goal.uom_type, target_value=base_goal.target_value,
            target_date=base_goal.target_date, weightage=10, is_shared=True, shared_from_goal_id=base_goal.id
        )
        db.add(new_g)
    db.commit()
    return {"message": "Shared goals pushed"}

@router.put("/unlock-sheet/{sheet_id}")
def unlock_sheet(sheet_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403)
        
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404)
        
    sheet.status = "rework"
    db.commit()
    log_audit(db, current_user.id, "unlock", "goal_sheet", sheet.id)
    return {"message": "Sheet unlocked"}

@router.get("/audit-log")
def get_audit_log(entity_type: str = None, entity_id: int = None, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403)
        
    query = db.query(models.AuditLog)
    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(models.AuditLog.entity_id == entity_id)
        
    return query.order_by(models.AuditLog.id.desc()).all()
