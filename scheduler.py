from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from database import SessionLocal
from models import User, GoalSheet, Goal, Achievement, EscalationAlert, CycleConfig

APPROVAL_OVERDUE_DAYS = 3
CHECKIN_MISSING_DAYS = 7

def run_escalation_check():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        print(f"[Escalation] Running check at {now}")

        # 1. APPROVAL OVERDUE
        cutoff = now - timedelta(days=APPROVAL_OVERDUE_DAYS)
        overdue_sheets = db.query(GoalSheet).filter(
            GoalSheet.status == "submitted",
            GoalSheet.submitted_at <= cutoff
        ).all()

        for sheet in overdue_sheets:
            already_alerted = db.query(EscalationAlert).filter_by(
                goal_sheet_id=sheet.id,
                alert_type="approval_overdue",
                is_resolved=False
            ).first()
            if already_alerted:
                continue

            employee = db.query(User).get(sheet.employee_id)
            manager = db.query(User).get(employee.manager_id) if employee and employee.manager_id else None
            skip_level = db.query(User).get(manager.manager_id) if manager and manager.manager_id else None

            days_pending = (now - sheet.submitted_at).days
            alert = EscalationAlert(
                alert_type="approval_overdue",
                goal_sheet_id=sheet.id,
                employee_id=sheet.employee_id,
                escalated_to_id=skip_level.id if skip_level else None,
                reason=f"Goal sheet submitted {days_pending} days ago by {employee.name if employee else 'unknown'} and is still pending manager approval."
            )
            db.add(alert)
            print(f"[Escalation] Approval overdue alert created for sheet {sheet.id}")

            if skip_level:
                from notifications import send_escalation_email
                send_escalation_email(
                    to=skip_level.email,
                    escalated_name=employee.name if employee else "Employee",
                    manager_name=manager.name if manager else "Manager",
                    reason=alert.reason,
                    alert_type="approval_overdue"
                )

        # 2. CHECKIN MISSING
        active_cycle = db.query(CycleConfig).filter_by(is_active=True).first()
        if active_cycle:
            quarter_windows = {
                "Q1": active_cycle.q1_open,
                "Q2": active_cycle.q2_open,
                "Q3": active_cycle.q3_open,
                "Q4": active_cycle.q4_open,
            }
            for quarter, open_date in quarter_windows.items():
                if not open_date:
                    continue
                
                # Check if open_date is date or string
                if isinstance(open_date, str):
                    open_date = datetime.strptime(open_date, "%Y-%m-%d").date()
                
                # Convert date to datetime for comparison
                if type(open_date) is not datetime:
                    open_datetime = datetime.combine(open_date, datetime.min.time())
                else:
                    open_datetime = open_date

                if now < open_datetime + timedelta(days=CHECKIN_MISSING_DAYS):
                    continue

                approved_sheets = db.query(GoalSheet).filter_by(
                    cycle_year=active_cycle.cycle_year,
                    status="approved"
                ).all()

                for sheet in approved_sheets:
                    goals = db.query(Goal).filter_by(goal_sheet_id=sheet.id).all()
                    if not goals:
                        continue

                    has_achievement = db.query(Achievement).filter(
                        Achievement.goal_id.in_([g.id for g in goals]),
                        Achievement.quarter == quarter,
                        Achievement.actual_value != None
                    ).first()

                    if has_achievement:
                        continue

                    already_alerted = db.query(EscalationAlert).filter_by(
                        goal_sheet_id=sheet.id,
                        alert_type="checkin_missing",
                        is_resolved=False,
                        reason=quarter
                    ).first()
                    if already_alerted:
                        continue

                    employee = db.query(User).get(sheet.employee_id)
                    manager = db.query(User).get(employee.manager_id) if employee and employee.manager_id else None

                    alert = EscalationAlert(
                        alert_type="checkin_missing",
                        goal_sheet_id=sheet.id,
                        employee_id=sheet.employee_id,
                        escalated_to_id=manager.id if manager else None,
                        reason=quarter
                    )
                    db.add(alert)
                    print(f"[Escalation] Check-in missing alert for sheet {sheet.id}, {quarter}")

        db.commit()
        print(f"[Escalation] Check complete.")
    except Exception as e:
        db.rollback()
        print(f"[Escalation] Error: {e}")
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(run_escalation_check, "interval", hours=24, id="escalation_check")
