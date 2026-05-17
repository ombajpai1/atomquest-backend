from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from datetime import datetime

import models, schemas, auth
from database import get_db

emp_router = APIRouter(prefix="/goals", tags=["goals (employee)"])
mgr_router = APIRouter(prefix="/manager", tags=["goals (manager)"])

def log_audit(db: Session, user_id: int, action: str, entity_type: str, entity_id: int, old_value: dict = None, new_value: dict = None):
    log = models.AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=json.dumps(old_value) if old_value else None,
        new_value=json.dumps(new_value) if new_value else None
    )
    db.add(log)
    db.commit()

def compute_progress_score(uom_type, target, actual, target_date=None, actual_date=None):
    if uom_type == "min":
        return actual / target if target else 0
    if uom_type == "max":
        return target / actual if actual else 0
    if uom_type == "timeline":
        if actual_date and target_date:
            if actual_date <= target_date:
                return 1.0
            else:
                return 0.5
        return 0.0
    if uom_type == "zero":
        return 1.0 if actual == 0 else 0.0
    return 0.0

# --- EMPLOYEE ENDPOINTS ---

@emp_router.get("/my-sheet", response_model=schemas.GoalSheetResponse)
def get_my_sheet(cycle_year: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != 'employee':
        raise HTTPException(status_code=403, detail="Only employees can access this")
    
    sheet = db.query(models.GoalSheet).filter(
        models.GoalSheet.employee_id == current_user.id,
        models.GoalSheet.cycle_year == cycle_year
    ).first()
    
    if not sheet:
        sheet = models.GoalSheet(employee_id=current_user.id, cycle_year=cycle_year)
        db.add(sheet)
        db.commit()
        db.refresh(sheet)
        
    return sheet

@emp_router.post("/", response_model=schemas.GoalResponse)
def create_goal(goal_data: schemas.GoalCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role != 'employee':
        raise HTTPException(status_code=403, detail="Only employees can access this")
        
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.employee_id == current_user.id).order_by(models.GoalSheet.id.desc()).first()
    if not sheet or sheet.status not in ['draft', 'rework']:
        raise HTTPException(status_code=400, detail="Sheet is not in draft or rework status")
        
    goals = db.query(models.Goal).filter(models.Goal.goal_sheet_id == sheet.id).all()
    if len(goals) >= 8:
        raise HTTPException(status_code=400, detail="Maximum 8 goals allowed")
        
    if goal_data.weightage < 10:
        raise HTTPException(status_code=400, detail="Minimum weightage per goal is 10%")
        
    total_weight = sum(g.weightage for g in goals) + goal_data.weightage
    if total_weight > 100:
        raise HTTPException(status_code=400, detail="Total weightage cannot exceed 100%")
        
    new_goal = models.Goal(**goal_data.model_dump(), goal_sheet_id=sheet.id)
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)
    
    log_audit(db, current_user.id, "create", "goal", new_goal.id, new_value=goal_data.model_dump(mode='json'))
    return new_goal

@emp_router.put("/{goal_id}", response_model=schemas.GoalResponse)
def update_goal(goal_id: int, goal_data: schemas.GoalUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.id == goal.goal_sheet_id).first()
    if sheet.employee_id != current_user.id or sheet.status not in ['draft', 'rework']:
        raise HTTPException(status_code=400, detail="Cannot edit goal")
        
    if goal.is_shared and goal_data.target_value is not None:
        raise HTTPException(status_code=400, detail="Cannot edit target of a shared goal")
        
    old_data = {"target_value": goal.target_value, "weightage": goal.weightage}
    
    if goal_data.target_value is not None:
        goal.target_value = goal_data.target_value
    if goal_data.weightage is not None:
        if goal_data.weightage < 10:
            raise HTTPException(status_code=400, detail="Minimum weightage per goal is 10%")
        goal.weightage = goal_data.weightage
        
    db.commit()
    db.refresh(goal)
    
    log_audit(db, current_user.id, "update", "goal", goal.id, old_value=old_data, new_value={"target_value": goal.target_value, "weightage": goal.weightage})
    return goal

@emp_router.delete("/{goal_id}")
def delete_goal(goal_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.id == goal.goal_sheet_id).first()
    if sheet.employee_id != current_user.id or sheet.status not in ['draft']:
        raise HTTPException(status_code=400, detail="Cannot delete goal")
        
    db.delete(goal)
    db.commit()
    return {"message": "Goal deleted"}

@emp_router.post("/submit")
def submit_sheet(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.employee_id == current_user.id).order_by(models.GoalSheet.id.desc()).first()
    if not sheet or sheet.status not in ['draft', 'rework']:
        raise HTTPException(status_code=400, detail="Sheet not in submitable state")
        
    goals = db.query(models.Goal).filter(models.Goal.goal_sheet_id == sheet.id).all()
    total_weight = sum(g.weightage for g in goals)
    if total_weight != 100:
        raise HTTPException(status_code=400, detail="Total weightage must equal exactly 100%")
        
    sheet.status = "submitted"
    sheet.submitted_at = datetime.utcnow()
    db.commit()
    
    manager = db.query(models.User).filter(models.User.id == current_user.manager_id).first()
    if manager:
        from notifications import send_submission_email
        send_submission_email(to=manager.email, manager_name=manager.name, employee_name=current_user.name, cycle_year=sheet.cycle_year)

    return {"message": "Goal sheet submitted successfully"}

@emp_router.get("/my-sheet/progress")
def get_progress(cycle_year: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.employee_id == current_user.id, models.GoalSheet.cycle_year == cycle_year).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found")
    
    result = []
    for g in sheet.goals:
        achievements = db.query(models.Achievement).filter(models.Achievement.goal_id == g.id).all()
        # For simplicity, calculate overall based on last achievement or sum
        actual_val = sum(a.actual_value for a in achievements if a.actual_value)
        actual_dt = max([a.actual_date for a in achievements if a.actual_date], default=None)
        
        score = compute_progress_score(g.uom_type, g.target_value, actual_val, g.target_date, actual_dt)
        result.append({"goal_id": g.id, "title": g.title, "progress_score": score * 100})
    return result

# --- MANAGER ENDPOINTS ---

@mgr_router.get("/team-sheets")
def get_team_sheets(cycle_year: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role not in ['manager', 'admin']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    reports = db.query(models.User).filter(models.User.manager_id == current_user.id).all()
    report_ids = [u.id for u in reports]
    
    sheets = db.query(models.GoalSheet).filter(
        models.GoalSheet.employee_id.in_(report_ids),
        models.GoalSheet.cycle_year == cycle_year
    ).all()
    return sheets

@mgr_router.get("/sheet/{sheet_id}", response_model=schemas.GoalSheetResponse)
def get_sheet(sheet_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found")
    return sheet

@mgr_router.put("/sheet/{sheet_id}/approve")
def approve_sheet(sheet_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.id == sheet_id).first()
    if not sheet or sheet.status != 'submitted':
        raise HTTPException(status_code=400, detail="Sheet not available for approval")
        
    sheet.status = "approved"
    sheet.approved_at = datetime.utcnow()
    sheet.approved_by = current_user.id
    db.commit()
    log_audit(db, current_user.id, "approve", "goal_sheet", sheet.id)
    
    employee = db.query(models.User).filter(models.User.id == sheet.employee_id).first()
    if employee:
        from notifications import send_approval_email
        send_approval_email(to=employee.email, employee_name=employee.name, cycle_year=sheet.cycle_year)
        
    return {"message": "Sheet approved"}

@mgr_router.put("/sheet/{sheet_id}/return")
def return_sheet(sheet_id: int, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    sheet = db.query(models.GoalSheet).filter(models.GoalSheet.id == sheet_id).first()
    if not sheet or sheet.status != 'submitted':
        raise HTTPException(status_code=400, detail="Sheet not available to return")
        
    sheet.status = "rework"
    db.commit()
    log_audit(db, current_user.id, "return", "goal_sheet", sheet.id, new_value={"remark": payload.get("remark")})

    employee = db.query(models.User).filter(models.User.id == sheet.employee_id).first()
    if employee:
        from notifications import send_rework_email
        send_rework_email(to=employee.email, employee_name=employee.name, cycle_year=sheet.cycle_year, remark=payload.get("remark"))

    return {"message": "Sheet returned for rework"}

@mgr_router.put("/goal/{goal_id}/edit")
def edit_goal_manager(goal_id: int, payload: dict, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404)
        
    old_data = {"target_value": goal.target_value, "weightage": goal.weightage}
    if "target_value" in payload:
        goal.target_value = payload["target_value"]
    if "weightage" in payload:
        goal.weightage = payload["weightage"]
        
    db.commit()
    log_audit(db, current_user.id, "update", "goal", goal.id, old_value=old_data, new_value=payload)
    return goal
