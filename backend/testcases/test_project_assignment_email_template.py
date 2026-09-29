from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from app.core.config import settings
from app.email_service.service import send_project_assignment_email
from app.email_service.templates import (
    get_project_assignment_email_html,
    get_project_assignment_email_text,
)


def test_project_assignment_email_text_content():
    """Verify plain text fallback contains all dynamic fields and no CTA button/link."""
    text = get_project_assignment_email_text(
        employee_name="Arjun Seereddy",
        project_name="my_project",
        project_code="PRJ020",
        description="Core HRMS development and testing.",
        start_date=date(2026, 9, 23),
        end_date=date(2027, 1, 23),
        status="PLANNED",
        role_name="Full Stack Developer",
        assigned_date=date(2026, 9, 23),
    )

    assert "Hello Arjun Seereddy," in text
    assert "Project: my_project" in text
    assert "Project Code: PRJ020" in text
    assert "Role: Full Stack Developer" in text
    assert "Assigned Date: 23 September 2026" in text
    assert "Start Date: 23 September 2026" in text
    assert "End Date: 23 January 2027" in text
    assert "Status: PLANNED" in text
    assert "Description: Core HRMS development and testing." in text
    assert "Please check your HRMS dashboard for more details about this project, tasks, and timelines." in text
    assert "HRMS Team" in text

    # Must NOT have any CTA buttons or links
    assert "Go to Dashboard" not in text
    assert "View Dashboard" not in text
    assert "Open Dashboard" not in text
    assert "View Project" not in text
    assert "Open Project" not in text
    assert "http://" not in text
    assert "https://" not in text


def test_project_assignment_email_html_structure_and_dynamic_rendering():
    """Verify HTML template structure, branding, dynamic fields, email-safe CID images, and absence of CTA buttons."""
    html = get_project_assignment_email_html(
        employee_name="Arjun Seereddy",
        project_name="my_project",
        project_code="PRJ020",
        description="Core HRMS development and testing.",
        start_date=date(2026, 9, 23),
        end_date=date(2027, 1, 23),
        status="PLANNED",
        role_name="Full Stack Developer",
        assigned_date=date(2026, 9, 23),
    )

    # Dynamic fields
    assert "Hello Arjun Seereddy," in html
    assert "my_project" in html
    assert "PRJ020" in html
    assert "Full Stack Developer" in html
    assert "23 September 2026" in html
    assert "23 January 2027" in html
    assert "PLANNED" in html
    assert "Core HRMS development and testing." in html

    # Essential brand and layout text
    assert "HRMS" in html
    assert "Enterprise Portal" in html
    assert "Streamlining People" in html
    assert "Projects and Growth" in html
    assert "PROJECT ASSIGNED" in html
    assert "Role" in html
    assert "Assigned Date" in html
    assert "Start Date" in html
    assert "End Date" in html
    assert "Status" in html
    assert "Description" in html
    assert "Please check your HRMS dashboard for more details about this project, tasks, and timelines." in html
    assert "HRMS Team" in html
    assert "Simplifying Workforce Management" in html

    # Container width
    assert 'width="640"' in html
    assert "max-width: 640px;" in html

    # CID image references (email-safe, Gmail compatible)
    assert 'src="cid:hrms-logo"' in html
    assert 'src="cid:project-icon"' in html
    assert 'src="cid:role-icon"' in html
    assert 'src="cid:calendar-icon"' in html
    assert 'src="cid:play-icon"' in html
    assert 'src="cid:calendar-check-icon"' in html
    assert 'src="cid:chart-icon"' in html
    assert 'src="cid:document-icon"' in html
    assert 'src="cid:info-icon"' in html

    # No SVG tags (Gmail strips SVGs)
    assert "<svg" not in html.lower()

    # STRICTLY NO CTA BUTTONS OR DASHBOARD LINKS
    assert "Go to Dashboard" not in html
    assert "View Dashboard" not in html
    assert "Open Dashboard" not in html
    assert "View Project" not in html
    assert "Open Project" not in html
    assert "<button" not in html.lower()
    assert "<a " not in html.lower()
    assert "href=" not in html.lower()


def test_project_assignment_email_different_statuses():
    """Verify different statuses render with appropriate badge styling and dynamic values."""
    for st, expected_badge in [("PLANNED", "PLANNED"), ("ACTIVE", "ACTIVE"), ("COMPLETED", "COMPLETED"), ("CANCELLED", "CANCELLED")]:
        html = get_project_assignment_email_html(
            employee_name="Jane Doe",
            project_name="Alpha Project",
            project_code="PRJ100",
            status=st,
        )
        assert expected_badge in html


def test_send_project_assignment_email_sends_multipart_related_message():
    """Verify send_project_assignment_email sends an email with plain text, HTML, and all inline CID PNG attachments."""
    recipient = "developer@example.com"

    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        send_project_assignment_email(
            recipient_email=recipient,
            employee_name="Jane Doe",
            project_name="Alpha Project",
            project_code="PRJ100",
            description="Project details description.",
            status="ACTIVE",
            role_name="Backend Engineer",
        )

        # Assert SMTP methods were called
        mock_smtp_class.assert_called_once_with(settings.SMTP_HOST, settings.SMTP_PORT)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
        mock_server.send_message.assert_called_once()

        # Inspect the message sent
        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg["To"] == recipient
        assert sent_msg["From"] == settings.SMTP_EMAIL
        assert sent_msg["Subject"] == "You have been assigned to a new project"

        # Verify multipart content structure:
        # Top-level: multipart/alternative (Plain text fallback + Rich HTML container)
        assert sent_msg.is_multipart()
        assert sent_msg.get_content_type() == "multipart/alternative"
        payloads = sent_msg.get_payload()
        assert len(payloads) == 2

        # Part 0 is plain text
        text_part = payloads[0]
        assert text_part.get_content_type() == "text/plain"
        assert "Alpha Project" in text_part.get_content()
        assert "PRJ100" in text_part.get_content()

        # Part 1 is multipart/related (HTML body + inline CID image attachments)
        related_part = payloads[1]
        assert related_part.get_content_type() == "multipart/related"
        subparts = related_part.get_payload()

        # HTML body
        html_subpart = subparts[0]
        assert html_subpart.get_content_type() == "text/html"
        html_body = html_subpart.get_content()
        assert "Alpha Project" in html_body
        assert "PRJ100" in html_body
        assert 'src="cid:hrms-logo"' in html_body
        assert 'src="cid:project-icon"' in html_body

        # Inline CID attachments
        attachment_cids = [p.get("Content-ID") for p in subparts[1:]]
        assert "<hrms-logo>" in attachment_cids
        assert "<project-icon>" in attachment_cids
        assert "<role-icon>" in attachment_cids
        assert "<calendar-icon>" in attachment_cids
        assert "<play-icon>" in attachment_cids
        assert "<calendar-check-icon>" in attachment_cids
        assert "<chart-icon>" in attachment_cids
        assert "<document-icon>" in attachment_cids
        assert "<info-icon>" in attachment_cids

        # Verify all attachments are PNG images with non-empty payloads
        for p in subparts[1:]:
            assert p.get_content_type() == "image/png"
            assert len(p.get_payload(decode=True)) > 0
