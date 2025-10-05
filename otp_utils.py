import random, string, hashlib, os
from email.message import EmailMessage
from datetime import datetime, timedelta

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def hash_otp(otp):
    return hashlib.sha256(otp.encode()).hexdigest()

async def send_otp_email(to_email, otp):
    # Lazy import so missing optional dependency doesn't break app import
    try:
        import aiosmtplib
    except ModuleNotFoundError:
        raise RuntimeError("aiosmtplib is required to send emails. Install with: python -m pip install aiosmtplib")

    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = to_email
    msg["Subject"] = "Your BytLearn OTP Code"
    msg.set_content(f"Your OTP code is: {otp}\nIt is valid for 10 minutes.")

    await aiosmtplib.send(
        msg,
        hostname=os.getenv("SMTP_HOST"),
        port=int(os.getenv("SMTP_PORT") or 587),
        username=os.getenv("SMTP_USER"),
        password=os.getenv("SMTP_PASSWORD"),
        start_tls=True,
    )