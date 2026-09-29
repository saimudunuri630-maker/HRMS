"""
Email templates for HRMS notifications and authentication.
Designed for high email client compatibility (Gmail, Outlook, iOS, Android, webmail).
Uses inline CID embedded image assets for 100% reliable icon rendering in Gmail.
"""
from datetime import datetime, timezone
import html as py_html


def get_otp_email_text(otp: str, expire_minutes: int = 10) -> str:
    """Plain-text fallback for OTP email."""
    return f"""Hello,

You have requested a login OTP for your HRMS account.
Use the OTP below to complete your login.

YOUR LOGIN OTP:
{otp}

This OTP is valid for {expire_minutes} minutes.

Keep Your Account Secure:
Do not share this OTP with anyone. If you did not request this OTP, please ignore this email.

Regards,
HRMS Team

This is an automated email from HRMS. Please do not reply.
"""


def get_otp_email_html(otp: str, expire_minutes: int = 10) -> str:
    """
    Generates a professional, modern, responsive HTML email template for HRMS Login OTP,
    matching the enterprise HRMS design system and reference image.
    Uses CID embedded PNG images for reliable rendering in Gmail.
    """
    otp_str = str(otp).strip()

    # Generate individual table cells for each digit
    digit_cells = []
    for idx, digit in enumerate(otp_str):
        if idx > 0:
            digit_cells.append('<td width="8" style="width: 8px; font-size: 1px; line-height: 1px;">&nbsp;</td>')
        digit_cells.append(
            f'<td align="center" valign="middle" width="52" height="62" '
            f'style="width: 52px; height: 62px; background-color: #e6effb; border-radius: 10px; '
            f'font-family: \'Inter\', -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; '
            f'font-size: 32px; font-weight: 800; color: #0b1a34; text-align: center; vertical-align: middle; '
            f'box-shadow: inset 0 1px 2px rgba(11, 26, 52, 0.04);">'
            f'{digit}'
            f'</td>'
        )
    digits_row_html = "".join(digit_cells)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>HRMS Login OTP</title>
  <!--[if mso]>
  <style type="text/css">
    body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
  </style>
  <![endif]-->
  <style type="text/css">
    body {{
      margin: 0;
      padding: 0;
      background-color: #f3f6fb;
      -webkit-text-size-adjust: 100%;
      -ms-text-size-adjust: 100%;
    }}
    table {{
      border-collapse: collapse;
      mso-table-lspace: 0pt;
      mso-table-rspace: 0pt;
    }}
    img {{
      border: 0;
      height: auto;
      line-height: 100%;
      outline: none;
      text-decoration: none;
      -ms-interpolation-mode: bicubic;
    }}
    @media only screen and (max-width: 660px) {{
      .email-container {{
        width: 100% !important;
        max-width: 100% !important;
        border-radius: 0 !important;
      }}
      .mobile-padding {{
        padding-left: 20px !important;
        padding-right: 20px !important;
      }}
      .header-mobile-col {{
        display: block !important;
        width: 100% !important;
        text-align: left !important;
        padding-bottom: 8px !important;
      }}
      .header-mobile-tagline {{
        text-align: left !important;
        margin-top: 6px !important;
      }}
      .footer-mobile-col {{
        display: block !important;
        width: 100% !important;
        padding-left: 0 !important;
        border-left: none !important;
        border-top: 1px solid #cbd5e1 !important;
        padding-top: 12px !important;
        margin-top: 12px !important;
      }}
    }}
  </style>
</head>
<body style="margin: 0; padding: 30px 10px; background-color: #f3f6fb; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  
  <!-- Outer Email Container Table -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f3f6fb; width: 100%;">
    <tr>
      <td align="center" valign="top">
        
        <!-- Main Card Container (640px wide max) -->
        <table role="presentation" class="email-container" width="640" cellpadding="0" cellspacing="0" border="0" style="width: 100%; max-width: 640px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 20px; overflow: hidden; box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05); margin: 0 auto;">
          
          <!-- ================= HEADER SECTION ================= -->
          <tr>
            <td style="background-color: #f0f6fe; border-bottom: 1px solid #e1edfb; padding: 22px 32px; position: relative;" class="mobile-padding">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <!-- Left: Brand Logo & Title -->
                  <td align="left" valign="middle" class="header-mobile-col">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td valign="middle" style="padding-right: 12px;">
                          <!-- HRMS User Icon Graphic (CID Embedded PNG) -->
                          <img src="cid:hrms-logo" width="38" height="32" alt="HRMS Logo" style="display: block; border: 0; outline: none; text-decoration: none; width: 38px; height: 32px;" border="0">
                        </td>
                        <td valign="middle">
                          <div style="font-size: 20px; font-weight: 800; color: #0b1a34; line-height: 1.1; letter-spacing: -0.3px;">HRMS</div>
                          <div style="font-size: 12px; font-weight: 500; color: #64748b; line-height: 1.2; margin-top: 2px;">Enterprise Portal</div>
                        </td>
                      </tr>
                    </table>
                  </td>
                  
                  <!-- Right: Professional Tagline -->
                  <td align="right" valign="middle" class="header-mobile-col">
                    <div class="header-mobile-tagline" style="font-size: 12px; line-height: 1.4; color: #64748b; font-weight: 500;">
                      Streamlining People,<br>Projects and Growth
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ================= GREETING & INTRO ================= -->
          <tr>
            <td style="padding: 32px 36px 16px 36px;" class="mobile-padding">
              <h1 style="margin: 0 0 12px 0; font-size: 24px; font-weight: 800; color: #0b1a34; line-height: 1.2;">Hello,</h1>
              <p style="margin: 0 0 4px 0; font-size: 14.5px; line-height: 1.6; color: #475569;">
                You have requested a login OTP for your HRMS account.
              </p>
              <p style="margin: 0; font-size: 14.5px; line-height: 1.6; color: #475569;">
                Use the OTP below to complete your login.
              </p>
            </td>
          </tr>

          <!-- ================= OTP CARD BLOCK ================= -->
          <tr>
            <td style="padding: 12px 36px 24px 36px;" class="mobile-padding">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f8fafd; border: 1px solid #e1edfb; border-radius: 16px; width: 100%;">
                <tr>
                  <td align="center" style="padding: 26px 20px 22px 20px;">
                    
                    <!-- Circular Lock Icon (CID Embedded PNG) -->
                    <img src="cid:lock-icon" width="46" height="46" alt="Security Lock" style="display: block; margin: 0 auto 12px auto; border: 0; outline: none; text-decoration: none; width: 46px; height: 46px;" border="0">

                    <!-- Header Label -->
                    <div style="font-size: 11.5px; font-weight: 700; color: #2563eb; letter-spacing: 1.8px; text-transform: uppercase; margin-bottom: 18px;">
                      YOUR LOGIN OTP
                    </div>

                    <!-- Centered OTP Digit Boxes -->
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin: 0 auto;">
                      <tr>
                        {digits_row_html}
                      </tr>
                    </table>

                    <!-- Expiration Line with Flanking Dividers -->
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top: 22px;">
                      <tr>
                        <td style="border-bottom: 1px solid #dce8f8; width: 22%; font-size: 1px; line-height: 1px;">&nbsp;</td>
                        <td align="center" style="padding: 0 12px; font-size: 13px; color: #475569; font-weight: 500; white-space: nowrap;">
                          This OTP is valid for <strong style="color: #2563eb; font-weight: 700;">{expire_minutes} minutes.</strong>
                        </td>
                        <td style="border-bottom: 1px solid #dce8f8; width: 22%; font-size: 1px; line-height: 1px;">&nbsp;</td>
                      </tr>
                    </table>

                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ================= SECURITY INFORMATION CARD ================= -->
          <tr>
            <td style="padding: 0 36px 26px 36px;" class="mobile-padding">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f1f7fe; border: 1px solid #e1edfb; border-radius: 14px; width: 100%;">
                <tr>
                  <td style="padding: 16px 20px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <!-- Shield Icon Badge (CID Embedded PNG) -->
                        <td width="42" valign="middle" align="center" style="width: 42px; padding-right: 14px;">
                          <img src="cid:shield-icon" width="40" height="40" alt="Security Shield" style="display: block; border: 0; outline: none; text-decoration: none; width: 40px; height: 40px;" border="0">
                        </td>

                        <!-- Security Text -->
                        <td valign="middle">
                          <div style="font-size: 13.5px; font-weight: 700; color: #0b1a34; margin-bottom: 3px;">
                            Keep Your Account Secure
                          </div>
                          <div style="font-size: 12.5px; line-height: 1.5; color: #475569;">
                            Do not share this OTP with anyone. If you did not request this OTP, please ignore this email.
                          </div>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ================= SIGN-OFF ================= -->
          <tr>
            <td style="padding: 0 36px 26px 36px;" class="mobile-padding">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="border-top: 1px solid #edf2f7; padding-top: 18px;">
                    <p style="margin: 0 0 2px 0; font-size: 13.5px; color: #475569;">Regards,</p>
                    <p style="margin: 0 0 8px 0; font-size: 14px; font-weight: 700; color: #0b1a34;">HRMS Team</p>
                    <p style="margin: 0; font-size: 12px; color: #94a3b8;">This is an automated email from HRMS. Please do not reply.</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ================= FOOTER SECTION ================= -->
          <tr>
            <td style="background-color: #eef5fd; border-top: 1px solid #e1edfb; padding: 22px 32px;" class="mobile-padding">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <!-- Left: Logo & Enterprise Portal (CID Embedded PNG) -->
                  <td align="left" valign="middle" width="160" style="width: 160px;" class="footer-mobile-col">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td valign="middle" style="padding-right: 10px;">
                          <img src="cid:hrms-logo" width="32" height="27" alt="HRMS Logo" style="display: block; border: 0; outline: none; text-decoration: none; width: 32px; height: 27px;" border="0">
                        </td>
                        <td valign="middle">
                          <div style="font-size: 16px; font-weight: 800; color: #0b1a34; line-height: 1;">HRMS</div>
                          <div style="font-size: 11px; font-weight: 500; color: #64748b; line-height: 1.2; margin-top: 2px;">Enterprise Portal</div>
                        </td>
                      </tr>
                    </table>
                  </td>

                  <!-- Right: Simplifying Workforce Management -->
                  <td align="left" valign="middle" style="border-left: 1px solid #cbd5e1; padding-left: 20px;" class="footer-mobile-col">
                    <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 3px;">
                      Simplifying Workforce Management
                    </div>
                    <div style="font-size: 11px; color: #64748b;">
                      Employees &bull; Performance &bull; Projects &bull; Leave &bull; More
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
        
      </td>
    </tr>
  </table>

</body>
</html>"""
    return html


def get_project_assignment_email_text(
    employee_name: str,
    project_name: str,
    project_code: str,
    description: str | None = None,
    start_date = None,
    end_date = None,
    status: str | None = None,
    role_name: str | None = None,
    assigned_date = None,
) -> str:
    """Plain-text fallback for project assignment email."""
    role_line = f"Role: {role_name}\n" if role_name else ""
    assigned_str = (
        assigned_date.strftime("%d %B %Y")
        if hasattr(assigned_date, "strftime")
        else (str(assigned_date) if assigned_date else datetime.now(timezone.utc).strftime("%d %B %Y"))
    )
    start_str = start_date.strftime("%d %B %Y") if hasattr(start_date, "strftime") else (str(start_date) if start_date else "Not specified")
    end_str = end_date.strftime("%d %B %Y") if hasattr(end_date, "strftime") else (str(end_date) if end_date else "Not specified")
    desc_line = f"Description: {description}\n" if description else ""
    status_str = f"Status: {status}\n" if status else ""

    return f"""Hello {employee_name},

You have been assigned to the following project:

Project: {project_name}
Project Code: {project_code}
{role_line}Assigned Date: {assigned_str}
Start Date: {start_str}
End Date: {end_str}
{status_str}{desc_line}Please check your HRMS dashboard for more details about this project, tasks, and timelines.

Regards,
HRMS Team

This is an automated email from HRMS. Please do not reply.
"""


def get_project_assignment_email_html(
    employee_name: str,
    project_name: str,
    project_code: str,
    description: str | None = None,
    start_date = None,
    end_date = None,
    status: str | None = None,
    role_name: str | None = None,
    assigned_date = None,
) -> str:
    """
    Generates a professional, modern, responsive HTML email template for HRMS Project Assignment,
    matching the reference image and HRMS enterprise visual language.
    Uses CID embedded PNG images for 100% reliable rendering in Gmail.
    """
    assigned_str = (
        assigned_date.strftime("%d %B %Y")
        if hasattr(assigned_date, "strftime")
        else (str(assigned_date) if assigned_date else datetime.now(timezone.utc).strftime("%d %B %Y"))
    )
    start_str = start_date.strftime("%d %B %Y") if hasattr(start_date, "strftime") else (str(start_date) if start_date else "Not specified")
    end_str = end_date.strftime("%d %B %Y") if hasattr(end_date, "strftime") else (str(end_date) if end_date else "Not specified")

    desc_str = description.strip() if description and description.strip() else "No description provided."
    role_str = role_name.strip() if role_name and role_name.strip() else "Team Member"
    status_raw = (status or "PLANNED").strip()
    status_upper = status_raw.upper()

    # Determine badge color based on project status
    if status_upper in ("PLANNED", "ACTIVE"):
        status_bg = "#dcfce7"
        status_fg = "#15803d"
    elif status_upper == "COMPLETED":
        status_bg = "#dbeafe"
        status_fg = "#1e40af"
    elif status_upper == "ON_HOLD":
        status_bg = "#fef3c7"
        status_fg = "#b45309"
    elif status_upper == "CANCELLED":
        status_bg = "#fee2e2"
        status_fg = "#b91c1c"
    else:
        status_bg = "#e0ecfb"
        status_fg = "#1e40af"

    # HTML escape dynamic strings
    esc_emp = py_html.escape(str(employee_name))
    esc_proj = py_html.escape(str(project_name))
    esc_code = py_html.escape(str(project_code))
    esc_role = py_html.escape(role_str)
    esc_desc = py_html.escape(desc_str)
    esc_status = py_html.escape(status_upper)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>HRMS Project Assignment</title>
  <!--[if mso]>
  <style type="text/css">
    body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
  </style>
  <![endif]-->
  <style type="text/css">
    body {{
      margin: 0;
      padding: 0;
      background-color: #f3f6fb;
      -webkit-text-size-adjust: 100%;
      -ms-text-size-adjust: 100%;
    }}
    table {{
      border-collapse: collapse;
      mso-table-lspace: 0pt;
      mso-table-rspace: 0pt;
    }}
    img {{
      border: 0;
      height: auto;
      line-height: 100%;
      outline: none;
      text-decoration: none;
      -ms-interpolation-mode: bicubic;
    }}
    @media only screen and (max-width: 660px) {{
      .email-container {{
        width: 100% !important;
        max-width: 100% !important;
        border-radius: 0 !important;
      }}
      .mobile-padding {{
        padding-left: 20px !important;
        padding-right: 20px !important;
      }}
      .header-mobile-col {{
        display: block !important;
        width: 100% !important;
        text-align: left !important;
        padding-bottom: 8px !important;
      }}
      .header-mobile-tagline {{
        text-align: left !important;
        margin-top: 6px !important;
      }}
      .footer-mobile-col {{
        display: block !important;
        width: 100% !important;
        padding-left: 0 !important;
        border-left: none !important;
        border-top: 1px solid #cbd5e1 !important;
        padding-top: 12px !important;
        margin-top: 12px !important;
      }}
    }}
  </style>
</head>
<body style="margin: 0; padding: 30px 10px; background-color: #f3f6fb; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  
  <!-- Outer Email Container Table -->
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f3f6fb; width: 100%;">
    <tr>
      <td align="center" valign="top">
        
        <!-- Main Card Container (640px wide max) -->
        <table role="presentation" class="email-container" width="640" cellpadding="0" cellspacing="0" border="0" style="width: 100%; max-width: 640px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 20px; overflow: hidden; box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05); margin: 0 auto;">
          
          <!-- ================= HEADER SECTION ================= -->
          <tr>
            <td style="background-color: #f0f6fe; border-bottom: 1px solid #e1edfb; padding: 22px 32px; position: relative;" class="mobile-padding">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <!-- Left: Brand Logo & Title -->
                  <td align="left" valign="middle" class="header-mobile-col">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td valign="middle" style="padding-right: 12px;">
                          <!-- HRMS User Icon Graphic (CID Embedded PNG) -->
                          <img src="cid:hrms-logo" width="38" height="32" alt="HRMS Logo" style="display: block; border: 0; outline: none; text-decoration: none; width: 38px; height: 32px;" border="0">
                        </td>
                        <td valign="middle">
                          <div style="font-size: 20px; font-weight: 800; color: #0b1a34; line-height: 1.1; letter-spacing: -0.3px;">HRMS</div>
                          <div style="font-size: 12px; font-weight: 500; color: #64748b; line-height: 1.2; margin-top: 2px;">Enterprise Portal</div>
                        </td>
                      </tr>
                    </table>
                  </td>
                  
                  <!-- Right: Professional Tagline -->
                  <td align="right" valign="middle" class="header-mobile-col">
                    <div class="header-mobile-tagline" style="font-size: 12px; line-height: 1.4; color: #64748b; font-weight: 500;">
                      Streamlining People,<br>Projects and Growth
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ================= GREETING & INTRO ================= -->
          <tr>
            <td style="padding: 32px 36px 16px 36px;" class="mobile-padding">
              <h1 style="margin: 0 0 12px 0; font-size: 24px; font-weight: 800; color: #0b1a34; line-height: 1.2;">Hello {esc_emp},</h1>
              <p style="margin: 0 0 4px 0; font-size: 14.5px; line-height: 1.6; color: #475569;">
                You have been assigned to a new project in HRMS.
              </p>
              <p style="margin: 0; font-size: 14.5px; line-height: 1.6; color: #475569;">
                Please find the project details below.
              </p>
            </td>
          </tr>

          <!-- ================= PROJECT ASSIGNMENT MAIN CARD ================= -->
          <tr>
            <td style="padding: 12px 36px 20px 36px;" class="mobile-padding">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f0f6fe; border: 1px solid #e1edfb; border-radius: 18px; width: 100%;">
                <tr>
                  <td style="padding: 24px 22px;">
                    
                    <!-- Top Summary Section with Folder Icon & Accent Bar -->
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <!-- Left: Circular Folder Icon -->
                        <td width="64" valign="middle" align="center" style="width: 64px; padding-right: 18px;">
                          <img src="cid:project-icon" width="56" height="56" alt="Project" style="display: block; border: 0; outline: none; text-decoration: none; width: 56px; height: 56px;" border="0">
                        </td>
                        <!-- Right: PROJECT ASSIGNED, Name, and Code pill with left accent line -->
                        <td valign="middle" style="border-left: 2px solid #93c5fa; padding-left: 16px;">
                          <div style="font-size: 11.5px; font-weight: 700; color: #2563eb; letter-spacing: 1.6px; text-transform: uppercase; margin-bottom: 4px;">
                            PROJECT ASSIGNED
                          </div>
                          <div style="font-size: 22px; font-weight: 800; color: #0b1a34; line-height: 1.2; margin-bottom: 8px; word-break: break-word;">
                            {esc_proj}
                          </div>
                          <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                            <tr>
                              <td style="background-color: #e0ecfb; border-radius: 8px; padding: 4px 12px; font-size: 12.5px; font-weight: 600; color: #1e40af;">
                                Project Code: {esc_code}
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </table>

                    <!-- Inner White Details Card with Structured Rows -->
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top: 20px; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; overflow: hidden; width: 100%;">
                      
                      <!-- Row 1: Role -->
                      <tr>
                        <td width="36" valign="middle" align="center" style="width: 36px; padding: 13px 8px 13px 18px; border-bottom: 1px solid #f1f5f9;">
                          <img src="cid:role-icon" width="28" height="28" alt="Role" style="display: block; border: 0; outline: none; text-decoration: none; width: 28px; height: 28px;" border="0">
                        </td>
                        <td width="130" valign="middle" style="width: 130px; padding: 13px 8px; font-size: 13.5px; color: #64748b; font-weight: 500; border-bottom: 1px solid #f1f5f9;">
                          Role
                        </td>
                        <td valign="middle" style="padding: 13px 18px 13px 8px; font-size: 14px; color: #0b1a34; font-weight: 600; border-bottom: 1px solid #f1f5f9; word-break: break-word;">
                          {esc_role}
                        </td>
                      </tr>

                      <!-- Row 2: Assigned Date -->
                      <tr>
                        <td width="36" valign="middle" align="center" style="width: 36px; padding: 13px 8px 13px 18px; border-bottom: 1px solid #f1f5f9;">
                          <img src="cid:calendar-icon" width="28" height="28" alt="Assigned Date" style="display: block; border: 0; outline: none; text-decoration: none; width: 28px; height: 28px;" border="0">
                        </td>
                        <td width="130" valign="middle" style="width: 130px; padding: 13px 8px; font-size: 13.5px; color: #64748b; font-weight: 500; border-bottom: 1px solid #f1f5f9;">
                          Assigned Date
                        </td>
                        <td valign="middle" style="padding: 13px 18px 13px 8px; font-size: 14px; color: #0b1a34; font-weight: 600; border-bottom: 1px solid #f1f5f9;">
                          {assigned_str}
                        </td>
                      </tr>

                      <!-- Row 3: Start Date -->
                      <tr>
                        <td width="36" valign="middle" align="center" style="width: 36px; padding: 13px 8px 13px 18px; border-bottom: 1px solid #f1f5f9;">
                          <img src="cid:play-icon" width="28" height="28" alt="Start Date" style="display: block; border: 0; outline: none; text-decoration: none; width: 28px; height: 28px;" border="0">
                        </td>
                        <td width="130" valign="middle" style="width: 130px; padding: 13px 8px; font-size: 13.5px; color: #64748b; font-weight: 500; border-bottom: 1px solid #f1f5f9;">
                          Start Date
                        </td>
                        <td valign="middle" style="padding: 13px 18px 13px 8px; font-size: 14px; color: #0b1a34; font-weight: 600; border-bottom: 1px solid #f1f5f9;">
                          {start_str}
                        </td>
                      </tr>

                      <!-- Row 4: End Date -->
                      <tr>
                        <td width="36" valign="middle" align="center" style="width: 36px; padding: 13px 8px 13px 18px; border-bottom: 1px solid #f1f5f9;">
                          <img src="cid:calendar-check-icon" width="28" height="28" alt="End Date" style="display: block; border: 0; outline: none; text-decoration: none; width: 28px; height: 28px;" border="0">
                        </td>
                        <td width="130" valign="middle" style="width: 130px; padding: 13px 8px; font-size: 13.5px; color: #64748b; font-weight: 500; border-bottom: 1px solid #f1f5f9;">
                          End Date
                        </td>
                        <td valign="middle" style="padding: 13px 18px 13px 8px; font-size: 14px; color: #0b1a34; font-weight: 600; border-bottom: 1px solid #f1f5f9;">
                          {end_str}
                        </td>
                      </tr>

                      <!-- Row 5: Status -->
                      <tr>
                        <td width="36" valign="middle" align="center" style="width: 36px; padding: 13px 8px 13px 18px; border-bottom: 1px solid #f1f5f9;">
                          <img src="cid:chart-icon" width="28" height="28" alt="Status" style="display: block; border: 0; outline: none; text-decoration: none; width: 28px; height: 28px;" border="0">
                        </td>
                        <td width="130" valign="middle" style="width: 130px; padding: 13px 8px; font-size: 13.5px; color: #64748b; font-weight: 500; border-bottom: 1px solid #f1f5f9;">
                          Status
                        </td>
                        <td valign="middle" style="padding: 13px 18px 13px 8px; border-bottom: 1px solid #f1f5f9;">
                          <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                            <tr>
                              <td style="background-color: {status_bg}; color: {status_fg}; border-radius: 10px; padding: 3px 12px; font-size: 11.5px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase;">
                                {esc_status}
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>

                      <!-- Row 6: Description -->
                      <tr>
                        <td width="36" valign="middle" align="center" style="width: 36px; padding: 13px 8px 13px 18px;">
                          <img src="cid:document-icon" width="28" height="28" alt="Description" style="display: block; border: 0; outline: none; text-decoration: none; width: 28px; height: 28px;" border="0">
                        </td>
                        <td width="130" valign="middle" style="width: 130px; padding: 13px 8px; font-size: 13.5px; color: #64748b; font-weight: 500;">
                          Description
                        </td>
                        <td valign="middle" style="padding: 13px 18px 13px 8px; font-size: 14px; color: #475569; line-height: 1.5; word-break: break-word;">
                          {esc_desc}
                        </td>
                      </tr>

                    </table>

                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ================= INFORMATIONAL NOTICE BLOCK (NO BUTTON/LINK) ================= -->
          <tr>
            <td style="padding: 0 36px 24px 36px;" class="mobile-padding">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f0f6fe; border: 1px solid #e1edfb; border-radius: 14px; width: 100%;">
                <tr>
                  <td style="padding: 16px 20px;">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <!-- Information Icon Badge (CID Embedded PNG) -->
                        <td width="38" valign="middle" align="center" style="width: 38px; padding-right: 14px;">
                          <img src="cid:info-icon" width="30" height="30" alt="Information" style="display: block; border: 0; outline: none; text-decoration: none; width: 30px; height: 30px;" border="0">
                        </td>

                        <!-- Informational Notice Text -->
                        <td valign="middle" style="font-size: 13.5px; line-height: 1.5; color: #475569;">
                          Please check your HRMS dashboard for more details about this project, tasks, and timelines.
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ================= SIGN-OFF ================= -->
          <tr>
            <td style="padding: 0 36px 26px 36px;" class="mobile-padding">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="border-top: 1px solid #edf2f7; padding-top: 18px;">
                    <p style="margin: 0 0 2px 0; font-size: 13.5px; color: #475569;">Regards,</p>
                    <p style="margin: 0 0 8px 0; font-size: 14px; font-weight: 700; color: #0b1a34;">HRMS Team</p>
                    <p style="margin: 0; font-size: 12px; color: #94a3b8;">This is an automated email from HRMS. Please do not reply.</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ================= FOOTER SECTION ================= -->
          <tr>
            <td style="background-color: #eef5fd; border-top: 1px solid #e1edfb; padding: 22px 32px;" class="mobile-padding">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <!-- Left: Logo & Enterprise Portal (CID Embedded PNG) -->
                  <td align="left" valign="middle" width="160" style="width: 160px;" class="footer-mobile-col">
                    <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                      <tr>
                        <td valign="middle" style="padding-right: 10px;">
                          <img src="cid:hrms-logo" width="32" height="27" alt="HRMS Logo" style="display: block; border: 0; outline: none; text-decoration: none; width: 32px; height: 27px;" border="0">
                        </td>
                        <td valign="middle">
                          <div style="font-size: 16px; font-weight: 800; color: #0b1a34; line-height: 1;">HRMS</div>
                          <div style="font-size: 11px; font-weight: 500; color: #64748b; line-height: 1.2; margin-top: 2px;">Enterprise Portal</div>
                        </td>
                      </tr>
                    </table>
                  </td>

                  <!-- Right: Simplifying Workforce Management -->
                  <td align="left" valign="middle" style="border-left: 1px solid #cbd5e1; padding-left: 20px;" class="footer-mobile-col">
                    <div style="font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 3px;">
                      Simplifying Workforce Management
                    </div>
                    <div style="font-size: 11px; color: #64748b;">
                      Employees &bull; Performance &bull; Projects &bull; Leave &bull; More
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
        
      </td>
    </tr>
  </table>

</body>
</html>"""
    return html

