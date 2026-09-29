from unittest.mock import MagicMock, patch
import pytest

from app.core.config import settings
from app.email_service.service import send_otp_email
from app.email_service.templates import get_otp_email_html, get_otp_email_text


def test_otp_email_text_content():
    """Verify plain text fallback contains dynamic OTP and expiry."""
    otp = "849201"
    expire_minutes = 10
    text = get_otp_email_text(otp=otp, expire_minutes=expire_minutes)

    assert otp in text
    assert f"{expire_minutes} minutes" in text
    assert "Keep Your Account Secure" in text
    assert "HRMS Team" in text


def test_otp_email_html_structure_and_dynamic_rendering():
    """Verify HTML template structure, branding, dynamic OTP digits, and CID image references."""
    test_otp = "739105"
    expire_minutes = 15
    html = get_otp_email_html(otp=test_otp, expire_minutes=expire_minutes)

    # Must contain each individual digit of the OTP
    for digit in test_otp:
        assert f">{digit}</td>" in html or f">{digit}</div>" in html or digit in html

    # Expiry duration must be dynamic
    assert f"{expire_minutes} minutes" in html

    # Must contain essential brand elements matching the reference design
    assert "HRMS" in html
    assert "Enterprise Portal" in html
    assert "Streamlining People" in html
    assert "Projects and Growth" in html
    assert "Hello," in html
    assert "You have requested a login OTP for your HRMS account." in html
    assert "YOUR LOGIN OTP" in html
    assert "Keep Your Account Secure" in html
    assert "Do not share this OTP with anyone" in html
    assert "HRMS Team" in html
    assert "Simplifying Workforce Management" in html
    assert "Employees &bull; Performance &bull; Projects &bull; Leave &bull; More" in html

    # Must contain CID image tags instead of SVGs (which Gmail strips)
    assert 'src="cid:hrms-logo"' in html
    assert 'src="cid:lock-icon"' in html
    assert 'src="cid:shield-icon"' in html
    assert "<svg" not in html.lower()

    # Must have proper desktop width container to avoid narrow ribbon collapse in Gmail
    assert 'width="640"' in html
    assert 'max-width: 640px;' in html

    # Confirm another random OTP renders its unique digits dynamically
    second_otp = "982341"
    second_html = get_otp_email_html(otp=second_otp, expire_minutes=10)
    for digit in second_otp:
        assert digit in second_html
    assert "982341" not in html
    assert "739105" not in second_html


def test_send_otp_email_sends_multipart_related_message():
    """Verify send_otp_email sends an email with plain text, HTML, and inline CID PNG attachments."""
    recipient = "employee@example.com"
    otp = "456789"

    with patch("smtplib.SMTP") as mock_smtp_class:
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        send_otp_email(recipient_email=recipient, otp=otp)

        # Assert SMTP methods were called
        mock_smtp_class.assert_called_once_with(settings.SMTP_HOST, settings.SMTP_PORT)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
        mock_server.send_message.assert_called_once()

        # Inspect the message sent
        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg["To"] == recipient
        assert sent_msg["From"] == settings.SMTP_EMAIL
        assert sent_msg["Subject"] == "HRMS Login OTP"

        # Verify multipart content structure:
        # Top-level: multipart/alternative (Plain text fallback + Rich HTML container)
        assert sent_msg.is_multipart()
        assert sent_msg.get_content_type() == "multipart/alternative"
        payloads = sent_msg.get_payload()
        assert len(payloads) == 2

        # Part 0 is plain text
        text_part = payloads[0]
        assert text_part.get_content_type() == "text/plain"
        assert otp in text_part.get_content()

        # Part 1 is multipart/related (HTML body + inline CID image attachments)
        related_part = payloads[1]
        assert related_part.get_content_type() == "multipart/related"
        subparts = related_part.get_payload()

        # HTML body
        html_subpart = subparts[0]
        assert html_subpart.get_content_type() == "text/html"
        html_body = html_subpart.get_content()
        assert otp[0] in html_body
        assert "YOUR LOGIN OTP" in html_body
        assert 'src="cid:hrms-logo"' in html_body
        assert 'src="cid:lock-icon"' in html_body
        assert 'src="cid:shield-icon"' in html_body

        # Inline CID attachments
        attachment_cids = [p.get("Content-ID") for p in subparts[1:]]
        assert "<hrms-logo>" in attachment_cids
        assert "<lock-icon>" in attachment_cids
        assert "<shield-icon>" in attachment_cids

        # Verify all attachments are PNG images with non-empty payloads
        for p in subparts[1:]:
            assert p.get_content_type() == "image/png"
            assert len(p.get_payload(decode=True)) > 0
