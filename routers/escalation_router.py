from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import EscalationAlert, User
from auth import get_current_user

router = APIRouter(prefix="/admin/escalations", tags=["escalations"])

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user

@router.get("/")
def list_escalations(
    resolved: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    alerts = db.query(EscalationAlert).filter_by(is_resolved=resolved).order_by(
        EscalationAlert.created_at.desc()
    ).all()
    return alerts

@router.put("/{alert_id}/resolve")
def resolve_escalation(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    alert = db.query(EscalationAlert).get(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by_id = current_user.id
    db.commit()
    return {"message": "Alert resolved", "alert_id": alert_id}

@router.post("/trigger")
def manually_trigger_escalation(
    current_user: User = Depends(require_admin)
):
    """Admin can manually trigger the escalation check without waiting 24 hours."""
    from scheduler import run_escalation_check
    run_escalation_check()
    return {"message": "Escalation check triggered successfully"}
