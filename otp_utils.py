import random                    # Used to pick random numbers (helps generate OTP codes)
import string                    # Used to access number characters for OTP
import hashlib                   # Used to convert OTP into a secure, scrambled format
import os                        # Used to get secret info from environment variables
from email.message import EmailMessage    # Tool for building an email message in Python
from datetime import datetime, timedelta  # For working with dates and times (for OTP expiry)

# NEW: Import database components to allow querying
from sqlalchemy.orm import Session
import models

# Function to generate a random OTP code (like '123456')
def generate_otp(length=6):
    # Picks random digits (0-9) of a given length and makes them into a string
    return ''.join(random.choices(string.digits, k=length))

# Function to scramble (hash) the OTP before saving to the database
def hash_otp(otp):
    # Turns OTP into a secure code using SHA-256 hashing algorithm
    return hashlib.sha256(otp.encode()).hexdigest()

# Function to send an OTP code to a user’s email address
# UPDATED: Now accepts db session and an optional name
async def send_otp_email(to_email: str, otp: str, db: Session, name: str | None = None):
    """
    Send OTP via SMTP when configured.
    If SMTP settings are missing or sending fails, fallback to console + log file.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT") or 587)
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    # --- UPDATED: Logic to find the user's name ---
    user_name = name  # Use the name if it was passed directly (e.g., from registration form)
    if not user_name:
        # If no name was provided, query the database for the user
        user = db.query(models.Student).filter(models.Student.email == to_email).first()
        user_name = user.name if user else "User" # Fallback to "User" if not found

    # --- UPDATED: Email body now uses the user's name ---
    generation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    email_body = f"""Dear {user_name},

Your one time PIN is: {otp}, and is valid for 10 minutes.
(Generated at {generation_time})

********************************
This is an auto-generated email.  Do not reply to this email.
"""

    # Build simple message
    msg = EmailMessage()
    msg["From"] = smtp_user or "no-reply@bytlearn.local"
    msg["To"] = to_email
    msg["Subject"] = "Your ByteLearn One Time PIN"
    msg.set_content(email_body)

    # If SMTP not configured, fallback to console + file log
    if not (smtp_host and smtp_user and smtp_password):
        print(f"[OTP FALLBACK] To: {to_email} OTP: {otp}")
        try:
            with open("otp_fallback.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.utcnow().isoformat()} | {to_email} | {otp}\n")
        except Exception:
            pass
        return

    # Try sending via aiosmtplib, but catch errors and fallback
    try:
        import aiosmtplib
    except ModuleNotFoundError:
        print("[OTP] aiosmtplib not installed — OTP will be logged to console")
        print(f"[OTP FALLBACK] To: {to_email} OTP: {otp}")
        try:
            with open("otp_fallback.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.utcnow().isoformat()} | {to_email} | {otp}\n")
        except Exception:
            pass
        return

    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            start_tls=True,
        )
        print(f"[OTP SENT] to {to_email}")
    except Exception as e:
        # connection / auth / network error — fallback to console + log
        print(f"[OTP ERROR] sending to {to_email}: {e}. Falling back to console log.")
        try:
            with open("otp_fallback.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.utcnow().isoformat()} | {to_email} | {otp} | ERROR: {e}\n")
        except Exception:
            pass
        print(f"[OTP FALLBACK] To: {to_email} OTP: {otp}")
