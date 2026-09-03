"""
TerraRisk AI - Production Email Dispatch Service
Handles transactional notifications, including 6-digit email verification OTPs,
critical hazard alerts, and system notifications via SMTP.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple
from dotenv import load_dotenv

# Load local environment variables from .env
load_dotenv()


def get_smtp_config() -> Tuple[str, int, str, str, str, bool]:
    """Dynamically read current SMTP configuration from environment."""
    load_dotenv(override=False)
    host = os.getenv("SMTP_HOST", "").strip()
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except (ValueError, TypeError):
        port = 587
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("SMTP_FROM", "").strip() or (f"TerraRisk AI <{user}>" if user else "TerraRisk AI <alerts@terrarisk.gov.in>")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    return host, port, user, password, from_addr, use_tls


def is_smtp_configured() -> bool:
    """Check if SMTP credentials are provided in the current environment."""
    host, _, user, password, _, _ = get_smtp_config()
    return bool(host and user and password)


def build_verification_html(recipient_name: str, code: str) -> str:
    """Generate responsive, high-contrast HTML email with security notice."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>TerraRisk AI Email Verification</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #0F172A;
      color: #F8FAFC;
      margin: 0;
      padding: 24px;
    }}
    .email-container {{
      max-width: 520px;
      margin: 0 auto;
      background: #1E293B;
      border: 1px solid #334155;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
    }}
    .header {{
      background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%);
      padding: 28px 24px;
      text-align: center;
      color: #FFFFFF;
    }}
    .brand-title {{
      margin: 0;
      font-size: 22px;
      font-weight: 800;
      letter-spacing: 0.5px;
    }}
    .brand-subtitle {{
      margin: 4px 0 0 0;
      font-size: 12px;
      opacity: 0.9;
      letter-spacing: 0.3px;
    }}
    .body-content {{
      padding: 28px 24px;
    }}
    .greeting {{
      font-size: 16px;
      font-weight: 600;
      color: #F8FAFC;
      margin-bottom: 12px;
    }}
    .description {{
      font-size: 14px;
      line-height: 1.5;
      color: #94A3B8;
      margin-bottom: 24px;
    }}
    .otp-box {{
      background: #0F172A;
      border: 2px dashed #0284C7;
      border-radius: 12px;
      padding: 18px;
      text-align: center;
      margin: 20px 0;
    }}
    .otp-code {{
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
      font-size: 32px;
      font-weight: 900;
      letter-spacing: 8px;
      color: #38BDF8;
      margin: 0;
    }}
    .expiry-note {{
      font-size: 12px;
      color: #F59E0B;
      margin-top: 8px;
      font-weight: 600;
    }}
    .security-notice {{
      font-size: 12px;
      color: #64748B;
      line-height: 1.4;
      border-top: 1px solid #334155;
      padding-top: 16px;
      margin-top: 24px;
    }}
    .footer {{
      background: #0F172A;
      padding: 14px 24px;
      text-align: center;
      font-size: 11px;
      color: #64748B;
      border-top: 1px solid #1E293B;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <h1 class="brand-title">TerraRisk AI</h1>
      <p class="brand-subtitle">Kerala Disaster Management Authority Early Warning Portal</p>
    </div>
    <div class="body-content">
      <div class="greeting">Hello {recipient_name},</div>
      <p class="description">
        Thank you for registering your profile with <strong>TerraRisk AI</strong>.
        Please use the following 6-digit verification code to complete your registration and activate your disaster early warning alerts.
      </p>

      <div class="otp-box">
        <div class="otp-code">{code}</div>
        <div class="expiry-note">Valid for 10 minutes</div>
      </div>

      <p class="description">
        If you did not initiate this request, please disregard this message. Your email address remains secure.
      </p>

      <div class="security-notice">
        <strong>Security Notice:</strong> TerraRisk AI personnel will never ask for your verification code or password. Do not share this code with anyone.
      </div>
    </div>
    <div class="footer">
      TerraRisk AI &bull; Kerala State Disaster Management Authority &bull; Automated System
    </div>
  </div>
</body>
</html>
"""


def send_verification_email(
    to_email: str,
    recipient_name: str,
    code: str
) -> Tuple[bool, str]:
    """
    Dispatch a 6-digit email verification OTP to the user.
    If SMTP is configured, sends via smtplib.
    If SMTP is not configured, logs to console and returns success so local dev is unblocked.
    """
    subject = f"{code} is your TerraRisk AI verification code"
    clean_email = to_email.strip().lower()
    clean_name = recipient_name.strip() or "Citizen"

    if not is_smtp_configured():
        # Development / Fallback mode: Print to backend console
        print(f"\n" + "=" * 65)
        print(f"📧 [DEV EMAIL SERVICE] Transactional Verification Dispatch")
        print(f"   To: {clean_name} <{clean_email}>")
        print(f"   Subject: {subject}")
        print(f"   🔑 6-Digit OTP: {code}")
        print(f"   Expires: 10 minutes")
        print("=" * 65 + "\n")
        return True, "Development mode: Code logged to terminal."

    # Production SMTP Mode
    host, port, user, password, from_addr, use_tls = get_smtp_config()
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = clean_email

        # Plaintext fallback
        text_content = (
            f"Hello {clean_name},\n\n"
            f"Your TerraRisk AI 6-digit verification code is: {code}\n"
            f"This code will expire in 10 minutes.\n\n"
            f"If you did not request this code, please ignore this email.\n\n"
            f"--\nTerraRisk AI & Kerala State Disaster Management Authority\n"
        )
        html_content = build_verification_html(clean_name, code)

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=12.0)
        else:
            server = smtplib.SMTP(host, port, timeout=12.0)
            if use_tls:
                server.starttls()

        server.login(user, password)
        server.sendmail(from_addr, [clean_email], msg.as_string())
        server.quit()

        print(f"[OK] Verification email successfully delivered to {clean_email}")
        return True, f"Verification email dispatched to {clean_email}"
    except Exception as e:
        err_msg = str(e)
        print(f"[ERROR] Failed to send email via SMTP ({host}:{port}): {err_msg}")
        # Always print the OTP to server console as emergency backup so user is never locked out
        print(f"🔑 [EMERGENCY CONSOLE OTP BACKUP]: {code} (for {clean_email})")
        return False, f"SMTP delivery failed: {err_msg}"
