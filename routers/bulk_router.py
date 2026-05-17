import csv
import io
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from models import User, GoalSheet, Goal
from auth import get_current_user

router = APIRouter(prefix="/admin", tags=["bulk"])

def require_admin(current_user: User = Depends(get_current_user)):
    from fastapi import HTTPException
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

TEMPLATE_HEADERS = ["employee_email", "thrust_area", "title", "description", "uom_type", "target_value", "target_date", "weightage"]
TEMPLATE_EXAMPLE = ["emp1@company.com", "Revenue Growth", "Increase Q1 Sales", "Achieve 15% growth", "min", "1000000", "", "30"]
VALID_UOM_TYPES = {"min", "max", "timeline", "zero"}

@router.get("/bulk-import-template")
def download_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(TEMPLATE_HEADERS)
    writer.writerow(TEMPLATE_EXAMPLE)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=goal_import_template.csv"}
    )

@router.post("/bulk-import-goals")
async def bulk_import_goals(
    file: UploadFile = File(...),
    cycle_year: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    content = await file.read()
    try:
        decoded = content.decode("utf-8")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))

    required_headers = {"employee_email", "thrust_area", "title", "uom_type", "target_value", "weightage"}
    if not required_headers.issubset(set(reader.fieldnames or [])):
        return {
            "error": f"CSV missing required columns. Required: {required_headers}",
            "success": [],
            "failed": []
        }

    results = {"total": 0, "success": [], "failed": []}

    for i, row in enumerate(reader):
        row_num = i + 2  # row 1 is header
        results["total"] += 1
        try:
            email = row.get("employee_email", "").strip()
            employee = db.query(User).filter(User.email == email).first()
            if not employee:
                raise ValueError(f"No employee found with email '{email}'")
            if employee.role != "employee":
                raise ValueError(f"User '{email}' is not an employee")

            uom_type = row.get("uom_type", "").strip().lower()
            if uom_type not in VALID_UOM_TYPES:
                raise ValueError(f"uom_type must be one of {VALID_UOM_TYPES}")

            try:
                weightage = float(row.get("weightage", 0))
            except ValueError:
                raise ValueError("weightage must be a number")
            if weightage < 10:
                raise ValueError("weightage must be at least 10%")
            if weightage > 100:
                raise ValueError("weightage cannot exceed 100%")

            try:
                target_value = float(row.get("target_value", 0)) if row.get("target_value") else 0.0
            except ValueError:
                raise ValueError("target_value must be a number")

            sheet = db.query(GoalSheet).filter_by(
                employee_id=employee.id,
                cycle_year=cycle_year
            ).first()
            if not sheet:
                sheet = GoalSheet(
                    employee_id=employee.id,
                    cycle_year=cycle_year,
                    status="draft"
                )
                db.add(sheet)
                db.flush()

            if sheet.status not in ("draft", "rework"):
                raise ValueError(f"GoalSheet is '{sheet.status}' — cannot add goals")

            existing_count = db.query(Goal).filter_by(goal_sheet_id=sheet.id).count()
            if existing_count >= 8:
                raise ValueError("Employee already has 8 goals (maximum reached)")

            existing_weightage = db.query(Goal).filter_by(goal_sheet_id=sheet.id).all()
            total_used = sum(g.weightage for g in existing_weightage)
            if total_used + weightage > 100:
                raise ValueError(f"Adding {weightage}% would exceed 100% (currently at {total_used}%)")

            target_date_val = row.get("target_date")
            target_date_parsed = None
            if target_date_val and target_date_val.strip():
                from datetime import datetime
                try:
                    target_date_parsed = datetime.strptime(target_date_val.strip(), "%Y-%m-%d").date()
                except ValueError:
                    pass # ignore or raise, we'll just ignore for now if bad format

            goal = Goal(
                goal_sheet_id=sheet.id,
                thrust_area=row.get("thrust_area", "").strip(),
                title=row.get("title", "").strip(),
                description=row.get("description", "").strip(),
                uom_type=uom_type,
                target_value=target_value,
                target_date=target_date_parsed,
                weightage=weightage,
                status="not_started"
            )
            db.add(goal)
            db.commit()

            results["success"].append({
                "row": row_num,
                "employee": email,
                "goal_title": goal.title
            })

        except Exception as e:
            db.rollback()
            results["failed"].append({
                "row": row_num,
                "employee": row.get("employee_email", "unknown"),
                "reason": str(e)
            })

    results["summary"] = f"{len(results['success'])} imported, {len(results['failed'])} failed out of {results['total']} rows"
    return results
