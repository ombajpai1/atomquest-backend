from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import StringIO
import csv

import models, auth
from database import get_db
from routers.goals_router import compute_progress_score

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/achievement-report")
def get_achievement_report(cycle_year: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role not in ['manager', 'admin']:
        raise HTTPException(status_code=403)
        
    users = db.query(models.User).filter(models.User.role == 'employee').all()
    if current_user.role == 'manager':
        users = [u for u in users if u.manager_id == current_user.id]
        
    result = []
    for u in users:
        sheet = db.query(models.GoalSheet).filter(models.GoalSheet.employee_id == u.id, models.GoalSheet.cycle_year == cycle_year).first()
        if not sheet:
            continue
            
        for g in sheet.goals:
            achs = {a.quarter: a.actual_value for a in db.query(models.Achievement).filter(models.Achievement.goal_id == g.id).all()}
            actual_val = sum(v for v in achs.values() if v is not None)
            
            # Simple fallback for actual_date for report
            achs_dates = [a.actual_date for a in g.achievements if a.actual_date]
            actual_date = max(achs_dates) if achs_dates else None
            
            score = compute_progress_score(g.uom_type, g.target_value, actual_val, g.target_date, actual_date) * 100
            
            result.append({
                "employee_name": u.name,
                "department": u.department,
                "thrust_area": g.thrust_area,
                "goal_title": g.title,
                "uom": g.uom_type,
                "target": g.target_value,
                "q1_actual": achs.get("Q1", ""),
                "q2_actual": achs.get("Q2", ""),
                "q3_actual": achs.get("Q3", ""),
                "q4_actual": achs.get("Q4", ""),
                "progress_score": score
            })
    return result

@router.get("/achievement-report/export")
def export_achievement_report(cycle_year: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    data = get_achievement_report(cycle_year, db, current_user)
    
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=["employee_name", "department", "thrust_area", "goal_title", "uom", "target", "q1_actual", "q2_actual", "q3_actual", "q4_actual", "progress_score"])
    writer.writeheader()
    writer.writerows(data)
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=achievement_report_{cycle_year}.csv"}
    )

@router.get("/completion-dashboard")
def get_completion_dashboard(cycle_year: int, quarter: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.role not in ['manager', 'admin']:
        raise HTTPException(status_code=403)
        
    users = db.query(models.User).filter(models.User.role == 'employee').all()
    if current_user.role == 'manager':
        users = [u for u in users if u.manager_id == current_user.id]
        
    result = []
    for u in users:
        sheet = db.query(models.GoalSheet).filter(models.GoalSheet.employee_id == u.id, models.GoalSheet.cycle_year == cycle_year).first()
        status = "Not Started"
        if sheet:
            achs = db.query(models.Achievement).join(models.Goal).filter(models.Goal.goal_sheet_id == sheet.id, models.Achievement.quarter == quarter).all()
            if len(achs) > 0 and len(achs) >= len(sheet.goals):
                status = "Completed"
            elif len(achs) > 0:
                status = "In Progress"
                
        result.append({
            "employee_name": u.name,
            "manager_id": u.manager_id,
            "status": status
        })
    return result
