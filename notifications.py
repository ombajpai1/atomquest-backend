import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def _send(to: str, subject: str, html_body: str):
    """Internal send function. Never raises — logs errors silently."""
    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_email or not smtp_password:
        print(f"[Notifications] SMTP not configured. Skipping email to {to}")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"AtomQuest Portal <{smtp_email}>"
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to, msg.as_string())
        print(f"[Notifications] Email sent to {to}: {subject}")
    except Exception as e:
        print(f"[Notifications] Failed to send email to {to}: {e}")

def send_approval_email(to: str, employee_name: str, cycle_year: int):
    subject = f"✅ Your Goal Sheet for {cycle_year} has been Approved"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #2ecc71;">Goal Sheet Approved</h2>
        <p>Hi <strong>{employee_name}</strong>,</p>
        <p>Great news! Your goal sheet for <strong>{cycle_year}</strong> has been approved by your manager.</p>
        <p>You can now start logging your quarterly achievements on the portal.</p>
        <br>
        <p style="color: #888; font-size: 12px;">AtomQuest Goal Tracking Portal</p>
    </div>
    """
    _send(to, subject, body)

def send_rework_email(to: str, employee_name: str, cycle_year: int, remark: str):
    subject = f"🔁 Your Goal Sheet for {cycle_year} needs Revision"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #e67e22;">Goal Sheet Returned for Rework</h2>
        <p>Hi <strong>{employee_name}</strong>,</p>
        <p>Your goal sheet for <strong>{cycle_year}</strong> has been returned by your manager for revision.</p>
        <div style="background: #fff3cd; border-left: 4px solid #e67e22; padding: 12px; margin: 16px 0;">
            <strong>Manager's Remark:</strong><br>{remark}
        </div>
        <p>Please log in to the portal, update your goals, and resubmit.</p>
        <br>
        <p style="color: #888; font-size: 12px;">AtomQuest Goal Tracking Portal</p>
    </div>
    """
    _send(to, subject, body)

def send_submission_email(to: str, manager_name: str, employee_name: str, cycle_year: int):
    subject = f"📋 {employee_name}'s Goal Sheet Awaiting Your Approval"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #3498db;">Goal Sheet Pending Approval</h2>
        <p>Hi <strong>{manager_name}</strong>,</p>
        <p><strong>{employee_name}</strong> has submitted their goal sheet for <strong>{cycle_year}</strong> and it is awaiting your approval.</p>
        <p>Please log in to the portal to review and approve or return for revision.</p>
        <br>
        <p style="color: #888; font-size: 12px;">AtomQuest Goal Tracking Portal</p>
    </div>
    """
    _send(to, subject, body)

def send_escalation_email(to: str, escalated_name: str, manager_name: str, reason: str, alert_type: str):
    label = "Approval Overdue" if alert_type == "approval_overdue" else "Check-in Missing"
    subject = f"⚠️ Escalation Alert: {label} — {escalated_name}"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #e74c3c;">Escalation Alert: {label}</h2>
        <p>This is an automated escalation from the AtomQuest Goal Tracking Portal.</p>
        <div style="background: #fdecea; border-left: 4px solid #e74c3c; padding: 12px; margin: 16px 0;">
            <strong>Employee:</strong> {escalated_name}<br>
            <strong>Manager:</strong> {manager_name}<br>
            <strong>Issue:</strong> {reason}
        </div>
        <p>Please take action or log in to the admin panel to resolve this alert.</p>
        <br>
        <p style="color: #888; font-size: 12px;">AtomQuest Goal Tracking Portal — Automated Alert System</p>
    </div>
    """
    _send(to, subject, body)
