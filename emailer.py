"""
JobAgent AI — Email Digest Sender (Week 3)
Sends the daily digest email with tailored PDFs attached via Gmail SMTP.
"""

import smtplib
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from config import EMAIL_SENDER, EMAIL_RECEIVER, EMAIL_APP_PASSWORD

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTML email template
# ---------------------------------------------------------------------------

def build_html_digest(applications: list[dict]) -> str:
    today = datetime.now().strftime("%A, %d %B %Y")

    job_cards = ""
    for i, app in enumerate(applications, 1):
        job   = app["job"]
        score = job.get("score", "N/A")
        reason = job.get("score_reason", "")
        stars = "⭐" * int(score) if isinstance(score, (int, float)) else ""

        job_cards += f"""
        <div style="background:#f8f9ff;border-left:4px solid #4f46e5;
                    border-radius:6px;padding:16px;margin-bottom:16px;">
          <h3 style="margin:0 0 4px;color:#1a1a2e;">#{i} {job.get('title','')}</h3>
          <p style="margin:0 0 6px;color:#555;font-size:14px;">
            🏢 {job.get('company','')} &nbsp;|&nbsp;
            📍 {job.get('location','')} &nbsp;|&nbsp;
            🔗 <a href="{job.get('url','#')}" style="color:#4f46e5;">View Job</a>
          </p>
          <p style="margin:0 0 4px;font-size:13px;">
            <b>Match score:</b> {score}/10 &nbsp; {stars}
          </p>
          <p style="margin:0;font-size:13px;color:#444;"><i>{reason}</i></p>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:Arial,sans-serif;max-width:640px;margin:auto;padding:24px;color:#222;">
      <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);
                  border-radius:10px;padding:24px;text-align:center;margin-bottom:24px;">
        <h1 style="color:#fff;margin:0;font-size:24px;">🤖 JobAgent AI</h1>
        <p style="color:#a0aec0;margin:6px 0 0;font-size:14px;">Your daily job digest — {today}</p>
      </div>

      <p style="font-size:15px;">Good morning! Here are your top <b>{len(applications)} job matches</b>
         for today. Tailored resumes and cover letters are attached as PDFs.</p>

      {job_cards}

      <div style="background:#f0fdf4;border-radius:6px;padding:14px;margin-top:20px;font-size:13px;color:#166534;">
        ✅ Just review, click Apply on the ones you like, and attach the matching PDF resume.
      </div>

      <p style="font-size:12px;color:#999;margin-top:24px;text-align:center;">
        Powered by JobAgent AI · Claude API · Built by you
      </p>
    </body>
    </html>
    """


# ---------------------------------------------------------------------------
# Email sender
# ---------------------------------------------------------------------------

def send_digest(applications: list[dict], pdf_paths: list[str]) -> bool:
    """
    Send the daily digest email with all PDFs attached.
    Returns True on success.
    """
    if not EMAIL_APP_PASSWORD or EMAIL_APP_PASSWORD == "your_gmail_app_password":
        logger.error("EMAIL_APP_PASSWORD not configured in config.py")
        return False

    today = datetime.now().strftime("%d %b %Y")
    subject = f"🤖 JobAgent — {len(applications)} Top Matches for {today}"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER

    # HTML body
    html_body = build_html_digest(applications)
    msg.attach(MIMEText(html_body, "html"))

    # Attach PDFs
    for pdf_path in pdf_paths:
        if not os.path.exists(pdf_path):
            logger.warning("PDF not found, skipping: %s", pdf_path)
            continue
        with open(pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=os.path.basename(pdf_path)
            )
            msg.attach(part)

    # Send via Gmail SMTP
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        logger.info("✅ Digest email sent to %s with %d PDFs", EMAIL_RECEIVER, len(pdf_paths))
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Gmail auth failed. Make sure you're using an App Password, not your real password.")
        logger.error("Create one at: https://myaccount.google.com/apppasswords")
        return False
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return False
