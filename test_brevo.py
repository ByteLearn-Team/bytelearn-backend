"""
Test Brevo API configuration
Run: python test_brevo.py
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

# Get credentials
api_key = os.getenv("BREVO_API_KEY", "").strip()
from_email = os.getenv("BREVO_FROM_EMAIL", "").strip()

print("=" * 60)
print("🔍 BREVO CONFIGURATION CHECK")
print("=" * 60)

# Check 1: Environment variables
print("\n1️⃣ Environment Variables:")
print(f"   BREVO_API_KEY: {'✅ SET' if api_key else '❌ NOT SET'}")
if api_key:
    print(f"   Key (first 15 chars): {api_key[:15]}...")
    print(f"   Key length: {len(api_key)} chars")
    print(f"   Key type: {'✅ API Key (xkeysib)' if api_key.startswith('xkeysib-') else '❌ SMTP Key (wrong type!)'}")
print(f"   BREVO_FROM_EMAIL: {from_email if from_email else '❌ NOT SET'}")

if not api_key:
    print("\n❌ ERROR: BREVO_API_KEY is not set in .env file!")
    exit(1)

if api_key.startswith('xsmtpsib-'):
    print("\n❌ ERROR: You're using an SMTP key! Need API key starting with 'xkeysib-'")
    exit(1)

if not from_email:
    print("\n❌ ERROR: BREVO_FROM_EMAIL is not set in .env file!")
    exit(1)

# Check 2: Test API key validity
print("\n2️⃣ Testing API Key...")
try:
    url = "https://api.brevo.com/v3/account"
    headers = {"api-key": api_key}
    
    response = httpx.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        print("   ✅ API key is VALID")
        account_info = response.json()
        print(f"   📧 Account email: {account_info.get('email', 'N/A')}")
        print(f"   📊 Plan: {account_info.get('plan', [{}])[0].get('type', 'N/A')}")
    elif response.status_code == 401:
        print("   ❌ API key is INVALID or EXPIRED")
        print(f"   Response: {response.text}")
        exit(1)
    else:
        print(f"   ⚠️  Unexpected status: {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"   ❌ Error checking API key: {e}")
    exit(1)

# Check 3: Test sending email
print("\n3️⃣ Testing Email Send...")
try:
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "sender": {"email": from_email, "name": "VeloxCT"},
        "to": [{"email": "kannanvyshnav77@gmail.com"}],
        "subject": "VeloxCT Test Email",
        "textContent": "This is a test email from VeloxCT. If you received this, Brevo is working!"
    }
    
    response = httpx.post(url, json=payload, headers=headers, timeout=15)
    
    if response.status_code == 201:
        print("   ✅ Email sent successfully!")
        result = response.json()
        print(f"   📬 Message ID: {result.get('messageId', 'N/A')}")
        print("\n✅ ALL TESTS PASSED! Check your email inbox.")
    elif response.status_code == 400:
        print("   ❌ Bad request - Check sender email verification")
        print(f"   Response: {response.text}")
    elif response.status_code == 401:
        print("   ❌ Unauthorized - API key issue")
        print(f"   Response: {response.text}")
    else:
        print(f"   ⚠️  Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"   ❌ Error sending email: {e}")
    exit(1)

print("\n" + "=" * 60)