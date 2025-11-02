import random
import string
import hashlib
import os
import time
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

def _send_via_sendgrid(api_key: str, from_email: str, to_email: str, subject: str, content: str, timeout: int = 15):
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
    r = httpx.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    return True

async def send_otp_email(to_email: str, otp: str, db: Session | None = None, name: str | None = None) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT") or 587)
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    timeout = int(os.getenv("SMTP_TIMEOUT") or 15)

    user_name = name
    if not user_name and db is not None:
        try:
            user = db.query(models.Student).filter(models.Student.email == to_email).first()
            user_name = user.name if user else "User"
        except Exception:
            user_name = "User"

    body = f"""Dear {user_name},

Your ByteLearn OTP is: {otp}
It is valid for 10 minutes.

If you did not request this, ignore this email.
"""
    msg = EmailMessage()
    msg["From"] = smtp_user or "no-reply@bytlearn.local"
    msg["To"] = to_email
    msg["Subject"] = "ByteLearn OTP"
    msg.set_content(body)

    # Try SMTP if configured
    if smtp_host and smtp_user and smtp_password:
        try:
            _send_via_smtp(smtp_host, smtp_port, smtp_user, smtp_password, msg, timeout=timeout)
            print(f"[OTP SENT] to {to_email} via SMTP")
            return True
        except Exception as e:
            print(f"[OTP ERROR] sending to {to_email}: {e}. Falling back...")
            _log_fallback(to_email, otp, str(e))

    # Fallback to SendGrid API if configured
    if sendgrid_key:
        try:
            _send_via_sendgrid(sendgrid_key, smtp_user or "no-reply@bytlearn.local", to_email, msg["Subject"], body, timeout=timeout)
            print(f"[OTP SENT] to {to_email} via SendGrid")
            return True
        except Exception as e:
            print(f"[OTP ERROR] SendGrid failed for {to_email}: {e}")
            _log_fallback(to_email, otp, str(e))

    # Final fallback: log & console
    _log_fallback(to_email, otp, "all-senders-failed")
    return False
