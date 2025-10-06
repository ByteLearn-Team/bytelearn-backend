import random                    # Used to pick random numbers (helps generate OTP codes)
import string                    # Used to access number characters for OTP
import hashlib                   # Used to convert OTP into a secure, scrambled format
import os                        # Used to get secret info from environment variables
from email.message import EmailMessage    # Tool for building an email message in Python
from datetime import datetime, timedelta  # For working with dates and times (for OTP expiry)

# Function to generate a random OTP code (like '123456')
def generate_otp(length=6):
    # Picks random digits (0-9) of a given length and makes them into a string
    return ''.join(random.choices(string.digits, k=length))

# Function to scramble (hash) the OTP before saving to the database
def hash_otp(otp):
    # Turns OTP into a secure code using SHA-256 hashing algorithm
    return hashlib.sha256(otp.encode()).hexdigest()

# Function to send an OTP code to a user’s email address
# (it runs asynchronously so it doesn’t freeze your app while sending)
async def send_otp_email(to_email, otp):
    # Try to import the email sending library (aiosmtplib)
    try:
        import aiosmtplib
    except ModuleNotFoundError:
        # If it's missing, show this message so the developer knows what to do
        raise RuntimeError("aiosmtplib is required to send emails. Install with: python -m pip install aiosmtplib")

    # Build the actual email message
    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_USER")                   # Who is sending the email (from env variable)
    msg["To"] = to_email                                   # Who should get the email (the student's address)
    msg["Subject"] = "Your ByteLearn OTP Code"             # The subject line for the email
    msg.set_content(f"Your OTP code is: {otp}\nIt is valid for 10 minutes.")  # Main content of the email

    # Actually send the email with the OTP, using secure settings from the .env file
    await aiosmtplib.send(
        msg,
        hostname=os.getenv("SMTP_HOST"),                   # Email server address
        port=int(os.getenv("SMTP_PORT") or 587),           # Email server port
        username=os.getenv("SMTP_USER"),                   # Sender account for email server
        password=os.getenv("SMTP_PASSWORD"),               # Password for email server
        start_tls=True,                                    # Encrypt the email connection for safety
    )
