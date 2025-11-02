import random
import string
import hashlib
import os
import time
import asyncio
from email.message import EmailMessage
from datetime import datetime
from sqlalchemy.orm import Session
import models
import smtplib
import httpx

def generate_otp(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))

def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()

def _log_fallback(to_email: str, otp: str, err: str | None = None):
    try:
        with open("otp_fallback.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.utcnow().isoformat()} | {to_email} | {otp} | ERR: {err}\n")
    except Exception:
        pass
    print(f"[OTP FALLBACK] To: {to_email} OTP: {otp} ERR: {err}")

def _send_via_smtp(host: str, port: int, user: str, password: str, msg: EmailMessage, timeout: int = 15):
    last_exc = None
    for attempt in range(1, 4):
        try:
            if port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                    smtp.login(user, password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                    smtp.ehlo()
                    smtp.starttls(timeout=timeout)
                    smtp.ehlo()
                    smtp.login(user, password)
                    smtp.send_message(msg)
            return True
        except Exception as e:
            last_exc = e
            time.sleep(1 + attempt * 1.5)
    raise last_exc

async def _send_via_sendgrid_async(api_key: str, from_email: str, to_email: str, subject: str, content: str, timeout: int = 15):
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "personalizations": [{"to":[{"email": to_email}], "subject": subject}],
        "from": {"email": from_email},
        "content": [{"type":"text/plain","value": content}]
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=payload, headers=headers)
        r.raise_for_status()
    return True

async def _send_via_brevo_async(api_key: str, from_email: str, from_name: str, to_email: str, subject: str, content: str, timeout: int = 15):
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "sender": {"email": from_email, "name": from_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": content
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=payload, headers=headers)
        r.raise_for_status()
    return True

async def send_otp_email(to_email: str, otp: str, db: Session | None = None, name: str | None = None) -> bool:
    """
    Try Brevo -> SendGrid -> SMTP (in that order). Log fallback to otp_fallback.log.
    Requires BREVO_API_KEY / SENDGRID_API_KEY / SMTP_* envs as appropriate.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT") or 587)
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    sendgrid_from = os.getenv("SENDGRID_FROM") or (smtp_user or "no-reply@bytlearn.local")
    brevo_key = os.getenv("BREVO_API_KEY")
    brevo_from = os.getenv("BREVO_FROM_EMAIL") or sendgrid_from
    brevo_from_name = os.getenv("BREVO_FROM_NAME") or "ByteLearn"
    timeout = int(os.getenv("SMTP_TIMEOUT") or 15)

    # Resolve user name
    user_name = name
    if not user_name and db is not None:
        try:
            user = db.query(models.Student).filter(models.Student.email == to_email).first()
            user_name = user.name if user else "User"
        except Exception:
            user_name = "User"

    subject = "ByteLearn OTP"
    body = f"""Dear {user_name},

Your ByteLearn OTP is: {otp}
It is valid for 10 minutes.

If you did not request this, ignore this email.
"""

    # 1) Brevo (preferred on Render if configured)
    if brevo_key:
        try:
            await _send_via_brevo_async(brevo_key, brevo_from, brevo_from_name, to_email, subject, body, timeout=timeout)
            print(f"[OTP SENT] to {to_email} via Brevo")
            return True
        except Exception as e:
            print(f"[OTP ERROR] Brevo failed for {to_email}: {e}")
            _log_fallback(to_email, otp, str(e))

    # 2) SendGrid API
    if sendgrid_key:
        try:
            await _send_via_sendgrid_async(sendgrid_key, sendgrid_from, to_email, subject, body, timeout=timeout)
            print(f"[OTP SENT] to {to_email} via SendGrid")
            return True
        except Exception as e:
            print(f"[OTP ERROR] SendGrid failed for {to_email}: {e}")
            _log_fallback(to_email, otp, str(e))

    # 3) SMTP fallback (run in thread to avoid blocking event loop)
    if smtp_host and smtp_user and smtp_password:
        try:
            msg = EmailMessage()
            msg["From"] = smtp_user
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.set_content(body)
            await asyncio.to_thread(_send_via_smtp, smtp_host, smtp_port, smtp_user, smtp_password, msg, timeout)
            print(f"[OTP SENT] to {to_email} via SMTP")
            return True
        except Exception as e:
            print(f"[OTP ERROR] SMTP failed for {to_email}: {e}")
            _log_fallback(to_email, otp, str(e))

    # Final fallback
    _log_fallback(to_email, otp, "all-senders-failed")
    return False
