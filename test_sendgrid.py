import os, httpx
key = os.getenv("SENDGRID_API_KEY")
if not key:
    raise SystemExit("Set SENDGRID_API_KEY in your environment")
resp = httpx.post(
  "https://api.sendgrid.com/v3/mail/send",
  headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"},
  json={
    "personalizations":[{"to":[{"email":"you@example.com"}]}],
    "from":{"email":"no-reply@bytlearn.local"},
    "subject":"Test",
    "content":[{"type":"text/plain","value":"SendGrid test"}]
  },
  timeout=15
)
print(resp.status_code, resp.text)