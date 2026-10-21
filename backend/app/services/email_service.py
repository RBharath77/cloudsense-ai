"""Real-time Email Dispatch Service via Gmail SMTP (SSL:465)
Authoritative enterprise email sender for OTP identity verification
and account recovery using authenticated Google App Password.
Dispatched on behalf of Warbytes (warbytes7@gmail.com).
"""

import smtplib
import secrets
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger("warbytes.email")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
GMAIL_SENDER = "warbytes7@gmail.com"
GMAIL_SENDER_NAME = "Warbytes"
GMAIL_APP_PASSWORD = "ngskwrmcwqontvjp"

def generate_ai_password(length: int = 14) -> str:
    """Generates an AI-grade secure temporary password combining uppercase, lowercase, digits, and symbols."""
    special_chars = "!@#$%^&*"
    chars = string.ascii_letters + string.digits + special_chars
    prefix = "CS#"
    rand_chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(special_chars),
    ]
    remaining = [secrets.choice(chars) for _ in range(max(0, length - len(prefix) - len(rand_chars)))]
    all_rand = rand_chars + remaining
    secrets.SystemRandom().shuffle(all_rand)
    return f"{prefix}{''.join(all_rand)}"

def send_otp_email(to_email: str, otp_code: str, purpose: str = "registration") -> dict:
    """Dispatches a secure 6-digit OTP verification email directly through Gmail SMTP.
    
    Supports:
      - 'registration': Email verification for new account activation
      - 'password_reset': Identity verification for account recovery
      - 'password_change': Identity verification to update password in settings
    """
    subject_map = {
        "registration": f"{otp_code} is your Warbytes Verification Code",
        "password_reset": f"{otp_code} is your Warbytes Password Reset Code",
        "password_change": f"{otp_code} is your Warbytes Password Change Code",
    }
    if purpose == "registration":
        action_text = "complete your account registration and verify your email address"
    elif purpose == "password_change":
        action_text = "verify your identity and update your workspace account password"
    else:
        action_text = "reset your account password"

    subject = subject_map.get(purpose, f"{otp_code} is your Warbytes Verification Code")

    # Plain text version for non-HTML mail clients
    text_content = f"""Warbytes Verification Code

Your 6-digit verification code is: {otp_code}

Please enter this code in your browser to {action_text} for {to_email}.
This code is valid for 15 minutes.

If you did not request this verification, please disregard this email.

Sent securely by Warbytes · warbytes7@gmail.com
Zero-Trust Enterprise IAM Security
"""

    # High-end modern HTML email
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #081026;
      color: #FFFFFF;
      margin: 0;
      padding: 30px 15px;
    }}
    .container {{
      max-width: 520px;
      margin: 0 auto;
      background: #0D1B3E;
      border: 1px solid rgba(65, 105, 225, 0.4);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 12px 35px rgba(0, 0, 0, 0.6);
    }}
    .header {{
      background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%);
      padding: 24px;
      text-align: center;
    }}
    .brand-title {{
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: #FFFFFF;
      margin: 0;
    }}
    .brand-subtitle {{
      font-size: 11px;
      color: #E0E7FF;
      margin-top: 4px;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }}
    .content {{
      padding: 32px 28px;
      text-align: center;
      background-color: #081026;
    }}
    .title {{
      font-size: 18px;
      font-weight: 700;
      color: #FFFFFF;
      margin-bottom: 8px;
    }}
    .desc {{
      font-size: 13px;
      color: #94A3B8;
      line-height: 1.5;
      margin-bottom: 24px;
    }}
    .otp-card {{
      background: rgba(65, 105, 225, 0.12);
      border: 1.5px dashed #4169E1;
      border-radius: 12px;
      padding: 18px 24px;
      display: inline-block;
      margin-bottom: 24px;
    }}
    .otp-code {{
      font-family: 'Courier New', Courier, monospace;
      font-size: 34px;
      font-weight: 900;
      color: #5AA9E6;
      letter-spacing: 8px;
    }}
    .meta {{
      font-size: 11px;
      color: #64748B;
      margin-top: 16px;
      line-height: 1.4;
    }}
    .footer {{
      padding: 18px 24px;
      background: #050B1A;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      text-align: center;
      font-size: 10px;
      color: #64748B;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="brand-title">Warbytes</div>
      <div class="brand-subtitle">Autonomous Security & Verification</div>
    </div>
    <div class="content">
      <div class="title">Verification Code</div>
      <div class="desc">
        Use the one-time verification code below to {action_text} for <strong>{to_email}</strong>.
      </div>
      <div class="otp-card">
        <div class="otp-code">{otp_code}</div>
      </div>
      <div class="meta">
        This OTP is valid for <strong>15 minutes</strong>.<br>
        If you did not initiate this request, you can safely ignore this email.
      </div>
    </div>
    <div class="footer">
      Sent securely by <strong>Warbytes</strong> · {GMAIL_SENDER}<br>
      Zero-Trust IAM & Security Verification Protocol
    </div>
  </div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{GMAIL_SENDER_NAME} <{GMAIL_SENDER}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        # Establish SSL connection with 12s timeout
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=12)
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_SENDER, [to_email], msg.as_string())
        server.quit()
        logger.info(f"Successfully sent Warbytes OTP email to {to_email} via Gmail SMTP")
        return {"success": True, "recipient": to_email}
    except Exception as e:
        logger.error(f"Gmail SMTP dispatch error to {to_email}: {e}")
        # Return error details without crashing backend callers
        return {"success": False, "recipient": to_email, "error": str(e)}

def send_invitation_email(
    to_email: str,
    username: str,
    role: str,
    temp_password: str,
    invited_by: str = "Workspace Administrator",
) -> dict:
    """Dispatches a professional workspace member invitation with AI-generated credentials via Gmail SMTP."""
    role_labels = {
        "ADMIN": "Admin",
        "FINOPS_ENGINEER": "Developer",
        "AUDITOR": "Audit",
        "VIEWER": "Visitor",
    }
    role_display = role_labels.get(role.upper(), role)
    subject = f"You have been invited to CloudSense AI Workspace ({role_display})"

    text_content = f"""Welcome to CloudSense AI!

Hello {username},

You have been invited by {invited_by} to join the CloudSense AI enterprise FinOps workspace with the role: {role_display}.

Your Login Credentials:
- Login Email / Username: {to_email}
- Temporary AI Password: {temp_password}
- Sign In URL: http://localhost:3000/login

Important Security Instructions:
Please sign in using your email and the temporary password above.
Once logged in, you can update your password at any time under Workspace Settings (Settings -> Account Security) using secure OTP email verification.

Sent securely by Warbytes · {GMAIL_SENDER}
Zero-Trust Enterprise IAM Security
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #081026;
      color: #FFFFFF;
      margin: 0;
      padding: 30px 15px;
    }}
    .container {{
      max-width: 540px;
      margin: 0 auto;
      background: #0D1B3E;
      border: 1px solid rgba(65, 105, 225, 0.4);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 12px 35px rgba(0, 0, 0, 0.6);
    }}
    .header {{
      background: linear-gradient(135deg, #1E3A8A 0%, #4169E1 100%);
      padding: 24px;
      text-align: center;
    }}
    .brand-title {{
      font-size: 22px;
      font-weight: 800;
      color: #FFFFFF;
      margin: 0;
    }}
    .brand-subtitle {{
      font-size: 11px;
      color: #E0E7FF;
      margin-top: 4px;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }}
    .content {{
      padding: 30px 28px;
      background-color: #081026;
    }}
    .greeting {{
      font-size: 16px;
      font-weight: 700;
      color: #FFFFFF;
      margin-bottom: 8px;
    }}
    .desc {{
      font-size: 13px;
      color: #94A3B8;
      line-height: 1.5;
      margin-bottom: 20px;
    }}
    .cred-card {{
      background: rgba(65, 105, 225, 0.1);
      border: 1px solid rgba(65, 105, 225, 0.35);
      border-radius: 12px;
      padding: 16px 20px;
      margin-bottom: 20px;
    }}
    .cred-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      font-size: 13px;
    }}
    .cred-row:last-child {{
      border-bottom: none;
    }}
    .cred-label {{
      color: #94A3B8;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .cred-value {{
      color: #FFFFFF;
      font-weight: 600;
    }}
    .cred-password {{
      font-family: 'Courier New', Courier, monospace;
      color: #5AA9E6;
      font-weight: 700;
      background: rgba(0, 0, 0, 0.3);
      padding: 3px 8px;
      border-radius: 6px;
      letter-spacing: 1px;
    }}
    .btn-container {{
      text-align: center;
      margin: 24px 0 16px 0;
    }}
    .btn {{
      display: inline-block;
      background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
      color: #FFFFFF !important;
      text-decoration: none;
      padding: 12px 28px;
      border-radius: 10px;
      font-weight: 600;
      font-size: 13px;
    }}
    .note {{
      font-size: 11px;
      color: #64748B;
      line-height: 1.5;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 16px;
    }}
    .footer {{
      padding: 16px 24px;
      background: #050B1A;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      text-align: center;
      font-size: 10px;
      color: #64748B;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="brand-title">Warbytes</div>
      <div class="brand-subtitle">CloudSense AI Workspace Invitation</div>
    </div>
    <div class="content">
      <div class="greeting">Hello {username},</div>
      <div class="desc">
        You have been invited by <strong>{invited_by}</strong> to join the CloudSense AI workspace. Your account has been provisioned with the <strong>{role_display}</strong> privilege tier.
      </div>
      <div class="cred-card">
        <div class="cred-row">
          <span class="cred-label">Login Username / Email</span>
          <span class="cred-value">{to_email}</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">Assigned Role</span>
          <span class="cred-value" style="color: #38BDF8;">{role_display}</span>
        </div>
        <div class="cred-row">
          <span class="cred-label">AI Temporary Password</span>
          <span class="cred-password">{temp_password}</span>
        </div>
      </div>
      <div class="btn-container">
        <a href="http://localhost:3000/login" class="btn">Sign In to CloudSense AI</a>
      </div>
      <div class="note">
        <strong>Security Notice:</strong> Please sign in with your email and the AI temporary password above. After logging in, you can change your password anytime under <strong>Workspace Settings &rarr; Account Security</strong> using secure email OTP verification.
      </div>
    </div>
    <div class="footer">
      Dispatched securely by <strong>Warbytes</strong> &middot; {GMAIL_SENDER}<br>
      Zero-Trust Multi-Tenant FinOps IAM Protocol
    </div>
  </div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{GMAIL_SENDER_NAME} <{GMAIL_SENDER}>"
    msg["To"] = to_email

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=12)
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_SENDER, [to_email], msg.as_string())
        server.quit()
        logger.info(f"Successfully dispatched workspace invitation email to {to_email}")
        return {"success": True, "recipient": to_email}
    except Exception as e:
        logger.error(f"Gmail SMTP invitation dispatch error to {to_email}: {e}")
        return {"success": False, "recipient": to_email, "error": str(e)}
