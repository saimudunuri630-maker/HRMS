import smtplib
from email.message import EmailMessage
from typing import Any, Optional
from app.core.config import settings
from app.email_service.assets import get_email_assets, get_project_assignment_email_assets
from app.email_service.templates import (
    get_otp_email_html,
    get_otp_email_text,
    get_project_assignment_email_html,
    get_project_assignment_email_text,
)

# Registry to ensure duplicate emails are never dispatched within the application lifecycle
_DISPATCHED_EMAILS_REGISTRY: set[str] = set()


def _send_smtp_email(
    to_email: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    assets: dict[str, bytes] | None = None,
    event: str = "GENERIC_EVENT",
    trigger: str = "Business event",
    entity_type: str | None = None,
    entity_id: Any | None = None,
    db: Any | None = None,
) -> bool:
    """
    Internal helper to dispatch emails via SMTP with structured traceable logging,
    strict RFC 5322 compliance, and duplicate dispatch protection.
    """
    clean_to = (to_email or "").strip().lower()
    if not clean_to:
        print("[EMAIL] UNEXPECTED TRIGGER")
        print(f"[EMAIL] Event: {event}")
        print("[EMAIL] Source: Empty recipient email provided. Dispatch aborted.")
        return False

    # Build unique deduplication key
    dispatch_key: str | None = None
    if entity_type and entity_id is not None:
        dispatch_key = f"{event}:{entity_type}:{entity_id}:{clean_to}"
    elif event not in ("AUTH_LOGIN_OTP",):
        # For non-OTP events without an explicit entity, deduplicate on event + recipient + subject
        dispatch_key = f"{event}:{clean_to}:{subject}"

    # 1. In-memory deduplication check
    if dispatch_key and dispatch_key in _DISPATCHED_EMAILS_REGISTRY:
        print(f"[EMAIL] Event: {event}")
        print(f"[EMAIL] Recipient: {clean_to}")
        print(f"[EMAIL] Trigger: {trigger}")
        print(f"[EMAIL] SKIPPED: Duplicate dispatch prevented (already sent in this session for {entity_type or 'action'} #{entity_id or 'N/A'})")
        return True

    # 2. Database audit log deduplication check (if db session and entity provided)
    if db and entity_type and entity_id is not None:
        try:
            from sqlalchemy import select
            from app.audit_service.models import AuditLog
            audit_action = f"EMAIL_DISPATCHED_{event}"[:100]
            existing_audit = db.scalar(
                select(AuditLog).where(
                    AuditLog.module == "EMAIL",
                    AuditLog.action == audit_action,
                    AuditLog.entity_type == str(entity_type)[:100],
                    AuditLog.entity_id == (int(entity_id) if str(entity_id).isdigit() else None),
                    AuditLog.new_value == clean_to,
                )
            )
            if existing_audit:
                print(f"[EMAIL] Event: {event}")
                print(f"[EMAIL] Recipient: {clean_to}")
                print(f"[EMAIL] Trigger: {trigger}")
                print(f"[EMAIL] SKIPPED: Duplicate dispatch prevented (audit log confirms previous delivery for {entity_type} #{entity_id})")
                if dispatch_key:
                    _DISPATCHED_EMAILS_REGISTRY.add(dispatch_key)
                return True
        except Exception:
            pass

    # Structured Traceable Logging (PART 4 requirements: never logs credentials or OTPs)
    print(f"[EMAIL] Event: {event}")
    print(f"[EMAIL] Recipient: {clean_to}")
    print(f"[EMAIL] Trigger: {trigger}")
    print("[EMAIL] Sending...")

    message = EmailMessage()
    message["Subject"] = subject
    from_email = getattr(settings, "SMTP_EMAIL", None) or "noreply@mediatize.com"
    message["From"] = from_email
    message["To"] = clean_to

    # Plain-text fallback for maximum client compatibility
    message.set_content(body)

    # Optional rich HTML email matching HRMS enterprise design
    if html_body:
        message.add_alternative(html_body, subtype="html")
        if assets:
            html_part = message.get_payload()[1]
            for cid, data in assets.items():
                html_part.add_related(data, "image", "png", cid=f"<{cid}>")

    try:
        smtp_host = getattr(settings, "SMTP_HOST", None)
        smtp_port = getattr(settings, "SMTP_PORT", 587)
        smtp_email = getattr(settings, "SMTP_EMAIL", None)
        smtp_password = getattr(settings, "SMTP_PASSWORD", None)

        if not smtp_host or not smtp_email:
            print("[EMAIL] Success (SMTP host/email not set; simulated delivery logged)")
            if dispatch_key:
                _DISPATCHED_EMAILS_REGISTRY.add(dispatch_key)
            return True

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            if smtp_password:
                server.login(smtp_email, smtp_password)
            server.send_message(message)

        print("[EMAIL] Success")
        if dispatch_key:
            _DISPATCHED_EMAILS_REGISTRY.add(dispatch_key)

        # Record in DB AuditLog for persistent duplicate protection
        if db and entity_type and entity_id is not None:
            try:
                from app.audit_service.models import AuditLog
                audit_action = f"EMAIL_DISPATCHED_{event}"[:100]
                audit = AuditLog(
                    action=audit_action,
                    module="EMAIL",
                    entity_type=str(entity_type)[:100],
                    entity_id=int(entity_id) if str(entity_id).isdigit() else None,
                    description=f"Sent {event} email to {clean_to} (Trigger: {trigger})",
                    new_value=clean_to,
                )
                db.add(audit)
                db.commit()
            except Exception:
                pass

        return True
    except Exception as e:
        print(f"[EMAIL] Failed: {e}")
        return False


def send_otp_email(
    recipient_email: str,
    otp: str,
    full_name: str | None = None,
    **kwargs: Any,
) -> bool:
    """
    Sends one-time passcode verification email to user (HR or Employee).
    Adheres strictly to Phase 24 requirements and rich HTML template standards.
    Never logs the OTP value or auth secrets.
    """
    expire_minutes = getattr(settings, "OTP_EXPIRE_MINUTES", 10)
    plain_text = get_otp_email_text(otp=otp, expire_minutes=expire_minutes)
    html_content = get_otp_email_html(otp=otp, expire_minutes=expire_minutes)
    assets = get_email_assets()

    return _send_smtp_email(
        to_email=recipient_email,
        subject="HRMS Login OTP",
        body=plain_text,
        html_body=html_content,
        assets=assets,
        event="AUTH_LOGIN_OTP",
        trigger="User requested login OTP",
    )


def send_profile_updated_email(
    recipient_email: str,
    full_name: str,
    updated_fields: list[str] | None = None,
    entity_id: Any | None = None,
    db: Any | None = None,
    **kwargs: Any,
) -> bool:
    """
    Sends confirmation email when an employee or HR profile is updated.
    Enforces Part 8 requirements.
    """
    clean_email = recipient_email.strip().lower()
    fields_list = "\n".join([f"- {field}" for field in (updated_fields or ["Personal Details"])])
    body = (
        f"Hello {full_name or 'User'},\n\n"
        f"Your HRMS profile was successfully updated.\n\n"
        f"Updated information:\n"
        f"{fields_list}\n\n"
        f"Employee number and email remain unchanged.\n\n"
        f"If you did not make this change, contact HR immediately.\n\n"
        f"Regards,\n"
        f"Mediatize HRMS Team"
    )
    return _send_smtp_email(
        to_email=clean_email,
        subject="Your HRMS profile was updated",
        body=body,
        event="PROFILE_UPDATED",
        trigger="User updated profile",
        entity_type="EMPLOYEE",
        entity_id=entity_id,
        db=db,
    )


def send_employee_welcome_email(
    recipient_email: str,
    first_name: str,
    employee_code: str,
    entity_id: Any | None = None,
    db: Any | None = None,
    **kwargs: Any,
) -> bool:
    """
    Sends onboarding email when HR creates a new employee account.
    Enforces Phase 23 requirements.
    """
    clean_email = recipient_email.strip().lower()
    body = (
        f"Welcome to Mediatize HRMS\n\n"
        f"Hello {first_name},\n\n"
        f"Your employee account has been created by HR administration.\n\n"
        f"Employee Number:\n"
        f"{employee_code}\n\n"
        f"Registered Corporate Email:\n"
        f"{clean_email}\n\n"
        f"Login Instructions:\n"
        f"1. Open the HRMS portal at /login\n"
        f"2. Enter your registered email ({clean_email})\n"
        f"3. An OTP verification code will be sent to your inbox\n"
        f"4. Enter the 6-digit code to access your Employee Dashboard\n\n"
        f"No password is required. Authentication is secured via one-time passcodes.\n\n"
        f"Regards,\n"
        f"Mediatize HRMS Team"
    )
    return _send_smtp_email(
        to_email=clean_email,
        subject="Welcome to Mediatize HRMS",
        body=body,
        event="EMPLOYEE_CREATED",
        trigger="HR created employee",
        entity_type="EMPLOYEE",
        entity_id=entity_id,
        db=db,
    )


def send_project_assignment_email(
    recipient_email: str,
    employee_name: str | None = None,
    first_name: str | None = None,
    project_name: str = "",
    project_code: str = "",
    description: str | None = None,
    start_date = None,
    end_date = None,
    expected_end_date = None,
    status: str | None = None,
    role_name: str | None = None,
    assigned_date = None,
    entity_id: Any | None = None,
    db: Any | None = None,
    **kwargs: Any,
) -> bool:
    """
    Sends project assignment notification email to employee.
    If role_name is provided, sends ONE consolidated email with both project & role details.
    Uses rich HTML email template with CID embedded images and plain-text fallback.
    """
    emp_name = employee_name or first_name or "Colleague"
    effective_end_date = end_date or expected_end_date

    plain_text = get_project_assignment_email_text(
        employee_name=emp_name,
        project_name=project_name,
        project_code=project_code,
        description=description,
        start_date=start_date,
        end_date=effective_end_date,
        status=status,
        role_name=role_name,
        assigned_date=assigned_date,
    )
    html_content = get_project_assignment_email_html(
        employee_name=emp_name,
        project_name=project_name,
        project_code=project_code,
        description=description,
        start_date=start_date,
        end_date=effective_end_date,
        status=status,
        role_name=role_name,
        assigned_date=assigned_date,
    )
    assets = get_project_assignment_email_assets()

    return _send_smtp_email(
        to_email=recipient_email,
        subject="You have been assigned to a new project",
        body=plain_text,
        html_body=html_content,
        assets=assets,
        event="PROJECT_ROLE_ASSIGNED",
        trigger="HR assigned employee to project role",
        entity_type="PROJECT_ASSIGNMENT",
        entity_id=entity_id,
        db=db,
    )


def send_project_role_assignment_email(
    recipient_email: str,
    first_name: str,
    project_name: str,
    role_name: str,
    previous_role: str | None = None,
    entity_id: Any | None = None,
    db: Any | None = None,
    **kwargs: Any,
) -> bool:
    """
    Sends role assignment or role update email when role is assigned/changed later.
    """
    clean_email = recipient_email.strip().lower()
    if previous_role and previous_role != role_name:
        role_body_part = (
            f"Your project role has been updated.\n\n"
            f"Project:\n"
            f"{project_name}\n\n"
            f"Previous Role:\n"
            f"{previous_role}\n\n"
            f"New Role:\n"
            f"{role_name}\n"
        )
    else:
        role_body_part = (
            f"Your project role has been updated.\n\n"
            f"Project:\n"
            f"{project_name}\n\n"
            f"Your project role:\n"
            f"{role_name}\n"
        )

    body = (
        f"Hello {first_name},\n\n"
        f"{role_body_part}\n"
        f"You can log in to Mediatize HRMS to view the project and your team.\n\n"
        f"Regards,\n"
        f"Mediatize HRMS Team"
    )
    return _send_smtp_email(
        to_email=clean_email,
        subject="Your project role has been updated — Mediatize HRMS",
        body=body,
        event="PROJECT_ROLE_UPDATED",
        trigger="HR updated employee project role",
        entity_type="PROJECT_ASSIGNMENT",
        entity_id=entity_id,
        db=db,
    )


def send_project_removal_email(
    recipient_email: str,
    first_name: str,
    project_name: str,
    project_code: str,
    previous_role: str | None = None,
    entity_id: Any | None = None,
    db: Any | None = None,
    **kwargs: Any,
) -> bool:
    """
    Sends notification when an employee is removed from a project.
    """
    clean_email = recipient_email.strip().lower()
    role_display = previous_role if previous_role else "Not assigned"

    body = (
        f"Hello {first_name},\n\n"
        f"You are no longer assigned to:\n"
        f"{project_name} ({project_code})\n\n"
        f"Your previous role:\n"
        f"{role_display}\n\n"
        f"The project assignment has been removed by HR.\n\n"
        f"Regards,\n"
        f"Mediatize HRMS Team"
    )
    return _send_smtp_email(
        to_email=clean_email,
        subject="You have been removed from a project — Mediatize HRMS",
        body=body,
        event="PROJECT_REMOVED",
        trigger="HR removed employee from project",
        entity_type="PROJECT_ASSIGNMENT",
        entity_id=entity_id,
        db=db,
    )


def send_announcement_published_email(
    recipient_email: str,
    first_name: str,
    title: str,
    content: str,
    priority: str,
    published_date: str,
    entity_id: Any | None = None,
    db: Any | None = None,
    **kwargs: Any,
) -> bool:
    """
    Sends company-wide announcement email to an active employee.
    Triggered only when HR explicitly publishes an announcement.
    """
    clean_email = recipient_email.strip().lower()
    body = (
        f"Mediatize HRMS Announcement\n\n"
        f"Hello {first_name},\n\n"
        f"A new company-wide announcement has been published:\n\n"
        f"Title: {title}\n"
        f"Priority: {priority}\n"
        f"Published Date: {published_date}\n\n"
        f"----------------------------------------\n"
        f"{content}\n"
        f"----------------------------------------\n\n"
        f"You can log in to Mediatize HRMS to view all announcements.\n\n"
        f"Regards,\n"
        f"Mediatize HRMS Team"
    )
    return _send_smtp_email(
        to_email=clean_email,
        subject=f"Mediatize Announcement: {title}",
        body=body,
        event="ANNOUNCEMENT_PUBLISHED",
        trigger="HR published announcement",
        entity_type="ANNOUNCEMENT",
        entity_id=entity_id,
        db=db,
    )


def send_leave_rejection_email(
    recipient_email: str,
    employee_name: str,
    leave_type_name: str,
    start_date: str,
    end_date: str,
    total_days: float,
    rejection_reason: str,
    entity_id: Any | None = None,
    db: Any | None = None,
    **kwargs: Any,
) -> bool:
    """
    Sends leave rejection notification email to employee with mandatory HR rejection remarks.
    """
    clean_email = recipient_email.strip().lower()
    days_str = f"{int(total_days)} day" if total_days == 1 else f"{total_days:g} days"
    body = (
        f"Leave Request Rejected\n\n"
        f"Hello {employee_name},\n\n"
        f"Your leave request for {leave_type_name} from {start_date} to {end_date} ({days_str}) has been rejected.\n\n"
        f"Reason:\n"
        f"{rejection_reason}\n\n"
        f"If you have questions regarding this decision, please consult with your HR administrator.\n\n"
        f"Regards,\n"
        f"Mediatize HRMS Team"
    )
    return _send_smtp_email(
        to_email=clean_email,
        subject="Leave Request Rejected",
        body=body,
        event="LEAVE_REJECTED",
        trigger="HR rejected leave request",
        entity_type="LEAVE_REQUEST",
        entity_id=entity_id,
        db=db,
    )


def send_leave_approval_email(
    recipient_email: str,
    employee_name: str,
    leave_type_name: str,
    start_date: str,
    end_date: str,
    total_days: float,
    approval_reason: str | None = None,
    entity_id: Any | None = None,
    db: Any | None = None,
    **kwargs: Any,
) -> bool:
    """
    Sends leave approval confirmation email to employee.
    """
    clean_email = recipient_email.strip().lower()
    days_str = f"{int(total_days)} day" if total_days == 1 else f"{total_days:g} days"
    remarks_line = f"\nRemarks: {approval_reason}\n" if approval_reason else ""
    body = (
        f"Leave Request Approved\n\n"
        f"Hello {employee_name},\n\n"
        f"Your leave request for {leave_type_name} from {start_date} to {end_date} ({days_str}) has been approved.{remarks_line}\n"
        f"Your leave balance has been updated.\n\n"
        f"Regards,\n"
        f"Mediatize HRMS Team"
    )
    return _send_smtp_email(
        to_email=clean_email,
        subject="Leave Request Approved",
        body=body,
        event="LEAVE_APPROVED",
        trigger="HR approved leave request",
        entity_type="LEAVE_REQUEST",
        entity_id=entity_id,
        db=db,
    )


def send_leave_revoked_email(
    recipient_email: str,
    employee_name: str,
    leave_type_name: str,
    start_date: str,
    end_date: str,
    total_days: float,
    previous_status: str,
    entity_id: Any | None = None,
    db: Any | None = None,
    **kwargs: Any,
) -> bool:
    """
    Sends leave revoke notification email to employee.
    """
    clean_email = recipient_email.strip().lower()
    days_str = f"{int(total_days)} day" if total_days == 1 else f"{total_days:g} days"
    body = (
        f"Leave Request Revoked\n\n"
        f"Hello {employee_name},\n\n"
        f"Your {leave_type_name} leave request from {start_date} to {end_date} ({days_str}) which was previously {previous_status} has been revoked by HR.\n\n"
        f"Your leave balance has been restored accordingly.\n\n"
        f"Regards,\n"
        f"Mediatize HRMS Team"
    )
    return _send_smtp_email(
        to_email=clean_email,
        subject="Leave Request Revoked",
        body=body,
        event="LEAVE_REVOKED",
        trigger="HR revoked leave request",
        entity_type="LEAVE_REQUEST",
        entity_id=entity_id,
        db=db,
    )