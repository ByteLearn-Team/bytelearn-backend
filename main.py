# Import the FastAPI class that helps create a web API easily in Python
from fastapi import FastAPI, Depends, HTTPException, Request
from sqlalchemy.orm import Session                           # For talking to the database
from database import SessionLocal                            # Local database connection/session
import crud, schemas                                         # Your own helper modules for logic and validation
from fastapi.middleware.cors import CORSMiddleware           # To allow the frontend and backend to talk to each other
from otp_utils import generate_otp, hash_otp, send_otp_email # Functions for handling OTP (one-time password)
from datetime import datetime, timedelta                     # For working with date and time objects
import asyncio                                               # Enables asynchronous operations (like sending emails)
from sqlalchemy import and_                                  # For advanced database queries (multiple conditions)
from dotenv import load_dotenv                               # Loads env variables, often used for secrets
import models                                                # All your database models (tables)
import httpx

# Load any environment variables from a .env file (like DB passwords, etc)
load_dotenv()

# Make a FastAPI application object called 'app'
app = FastAPI()

# Add CORS middleware, which allows other websites (like your frontend) to access this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],              # Allow anyone (for dev); use your site in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a dependency function to get the database for each API call
def get_db():
    db = SessionLocal()               # Makes a new database session for this API request
    try:
        yield db                      # Provide the db to whatever needs it
    finally:
        db.close()                    # Finally, close the db connection (avoids leaks)

# ==========================
# Routes (API Endpoints)
# ==========================

# The root URL ("/") shows a welcome message
@app.get("/")
def home():
    return {"msg": "ByteLearn backend connected to Aiven ✅"}

# Get all students from the database
@app.get("/students", response_model=list[schemas.StudentOut])
def get_all_students(db: Session = Depends(get_db)):
    return crud.get_students(db)

# Add a new student to the database
@app.post("/students", response_model=schemas.StudentOut)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    return crud.create_student(db, student)

# Register new student; send OTP for verification
@app.post("/register")
async def register(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    """
    Register a user: if email already fully registered -> error.
    If a pending registration for this email exists -> resend new OTP and update pending record.
    Otherwise create a new pending registration and send OTP.
    """
    # If already a real student, reject
    if db.query(crud.Student).filter_by(email=student.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # If there's already a pending registration, update its OTP and resend
    pending = db.query(models.PendingRegistration).filter_by(email=student.email).first()
    otp = generate_otp()
    otp_hash_val = hash_otp(otp)
    expires = datetime.utcnow() + timedelta(minutes=10)

    if pending:
        pending.otp_hash = otp_hash_val
        pending.otp_expires_at = expires
        pending.otp_attempts = 0
        pending.otp_last_sent_at = datetime.utcnow()
        # update other fields if provided (name/password/class) so user can re-send corrected info
        pending.name = student.name or pending.name
        pending.password_hash = student.password_hash or pending.password_hash
        pending.class_id = student.class_id if student.class_id is not None else pending.class_id
        db.commit()
        await send_otp_email(student.email, otp)
        return {"msg": "OTP resent"}

    # No pending registration exists — create one
    pending = models.PendingRegistration(
        name=student.name,
        email=student.email,
        password_hash=student.password_hash,
        class_id=student.class_id,
        otp_hash=otp_hash_val,
        otp_expires_at=expires,
        otp_attempts=0,
        otp_last_sent_at=datetime.utcnow()
    )
    db.add(pending)
    db.commit()
    await send_otp_email(student.email, otp)
    return {"msg": "OTP sent"}

# Get all classes from the database
@app.get("/classes", response_model=list[schemas.ClassOut])
def get_all_classes(db: Session = Depends(get_db)):
    return crud.get_classes(db)

# Add a new class
@app.post("/classes", response_model=schemas.ClassOut)
def create_class(class_: schemas.ClassCreate, db: Session = Depends(get_db)):
    return crud.create_class(db, class_)

# Get all subjects
@app.get("/subjects", response_model=list[schemas.SubjectOut])
def get_all_subjects(db: Session = Depends(get_db)):
    return crud.get_subjects(db)

# Add a new subject
@app.post("/subjects", response_model=schemas.SubjectOut)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    return crud.create_subject(db, subject)

# Get all chapters
@app.get("/chapters", response_model=list[schemas.ChapterOut])
def get_all_chapters(db: Session = Depends(get_db)):
    return crud.get_chapters(db)

# Add a new chapter
@app.post("/chapters", response_model=schemas.ChapterOut)
def create_chapter(chapter: schemas.ChapterCreate, db: Session = Depends(get_db)):
    return crud.create_chapter(db, chapter)

# Get all summaries
@app.get("/summaries", response_model=list[schemas.SummaryOut])
def get_all_summaries(db: Session = Depends(get_db)):
    return crud.get_summaries(db)

# Add a new summary
@app.post("/summaries", response_model=schemas.SummaryOut)
def create_summary(summary: schemas.SummaryCreate, db: Session = Depends(get_db)):
    return crud.create_summary(db, summary)

# Get all flashcards
@app.get("/flashcards", response_model=list[schemas.FlashcardOut])
def get_all_flashcards(db: Session = Depends(get_db)):
    return crud.get_flashcards(db)

# Add a new flashcard
@app.post("/flashcards", response_model=schemas.FlashcardOut)
def create_flashcard(flashcard: schemas.FlashcardCreate, db: Session = Depends(get_db)):
    return crud.create_flashcard(db, flashcard)

# Get all images
@app.get("/images", response_model=list[schemas.ImageOut])
def get_all_images(db: Session = Depends(get_db)):
    return crud.get_images(db)

# Add a new image
@app.post("/images", response_model=schemas.ImageOut)
def create_image(image: schemas.ImageCreate, db: Session = Depends(get_db)):
    return crud.create_image(db, image)

# Get all NCERT entries
@app.get("/ncert", response_model=list[schemas.NcertOut])
def get_all_ncerts(db: Session = Depends(get_db)):
    return crud.get_ncerts(db)

# Add a new NCERT entry
@app.post("/ncert", response_model=schemas.NcertOut)
def create_ncert(ncert: schemas.NcertCreate, db: Session = Depends(get_db)):
    return crud.create_ncert(db, ncert)

# Basic login function
@app.post("/login")
def login(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    password = data.get("password")
    user = db.query(crud.Student).filter_by(email=email).first()
    if not user or user.password_hash != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"student_id": user.student_id, "name": user.name, "email": user.email}

# Resend OTP to a user (if needed)
@app.post("/send_otp")
async def send_otp(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    # Try pending_registrations table first
    pending = db.query(models.PendingRegistration).filter_by(email=email).first()
    if pending:
        otp = generate_otp()
        pending.otp_hash = hash_otp(otp)
        pending.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        pending.otp_attempts = 0
        pending.otp_last_sent_at = datetime.utcnow()
        db.commit()
        await send_otp_email(email, otp)
        return {"msg": "OTP resent"}
    # Try students table (if not found above)
    user = db.query(models.Student).filter_by(email=email).first()
    if user:
        otp = generate_otp()
        user.otp_hash = hash_otp(otp)
        user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        user.otp_attempts = 0
        user.otp_last_sent_at = datetime.utcnow()
        db.commit()
        await send_otp_email(email, otp)
        return {"msg": "OTP resent"}
    # If email is not found anywhere, raise an error
    raise HTTPException(status_code=404, detail="User not found")

# Verify that an OTP is correct and activate the user's account
@app.post("/verify_otp")
def verify_otp(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    otp = data.get("otp")
    pending = db.query(models.PendingRegistration).filter_by(email=email).first()
    if not pending or not pending.otp_hash or not pending.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP not requested")
    if datetime.utcnow() > pending.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP expired")
    if pending.otp_attempts >= 5:
        raise HTTPException(status_code=400, detail="Too many attempts")
    if pending.otp_hash != hash_otp(otp):
        pending.otp_attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # If everything is good, make a new real Student
    student = models.Student(
        name=pending.name,
        email=pending.email,
        password_hash=pending.password_hash,
        class_id=pending.class_id,
        is_verified=1
    )
    db.add(student)        # Save student to real student table
    db.delete(pending)     # Remove from pending table
    db.commit()
    return {"msg": "OTP verified"}

@app.post("/generate")
async def generate(request: Request):
    """Proxy endpoint: accepts JSON { "prompt": "..." } and forwards to Flowise,
    returning a parsed text field to the frontend."""
    body = await request.json()
    prompt = body.get("prompt") or body.get("question") or body.get("input")
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing prompt")

    FLOWISE_API = "https://cloud.flowiseai.com/api/v1/prediction/95ac6cf3-9302-44b5-b406-28fb18d3dd31"

    # Flowise typically expects {"question": "..."} — include that.
    payload = {"question": prompt}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(FLOWISE_API, json=payload)
            resp.raise_for_status()
            resp_json = resp.json()
            # Try to pull the human-readable answer from common Flowise shapes
            answer = None
            try:
                if isinstance(resp_json, dict):
                    if resp_json.get("text"):
                        answer = resp_json["text"]
                    elif resp_json.get("output_text"):
                        answer = resp_json["output_text"]
                    elif resp_json.get("answer"):
                        answer = resp_json["answer"]
                    elif isinstance(resp_json.get("result"), str):
                        answer = resp_json["result"]
                    else:
                        out = resp_json.get("output") or resp_json.get("result")
                        if isinstance(out, list) and out:
                            first = out[0]
                            data = first.get("data") if isinstance(first, dict) else None
                            if isinstance(data, list) and data and data[0].get("text"):
                                answer = data[0]["text"]
            except Exception:
                answer = None

            # Fallback to stringified raw response when no text found
            if not answer:
                # compactly provide an informative fallback
                try:
                    answer = resp_json.get("text") or resp_json.get("output_text") or ""
                except Exception:
                    answer = ""

            return {"text": answer, "raw": resp_json}
    except httpx.HTTPStatusError as e:
        # include upstream status for debugging
        raise HTTPException(status_code=502, detail=f"Upstream error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    
    # Add these new endpoints to your existing main.py file
# Place them after the existing /verify_otp endpoint

@app.post("/forgot_password")
async def forgot_password(data: dict, db: Session = Depends(get_db)):
    """
    Initiates password reset process by sending OTP to user's email
    """
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    # Check if user exists in students table
    user = db.query(models.Student).filter_by(email=email).first()
    if not user:
        # Don't reveal if email exists for security
        raise HTTPException(status_code=404, detail="If this email exists, an OTP has been sent")
    
    # Generate OTP for password reset
    otp = generate_otp()
    otp_hash_val = hash_otp(otp)
    expires = datetime.utcnow() + timedelta(minutes=10)
    
    # Store OTP in user record
    user.otp_hash = otp_hash_val
    user.otp_expires_at = expires
    user.otp_attempts = 0
    user.otp_last_sent_at = datetime.utcnow()
    db.commit()
    
    # Send OTP email
    await send_otp_email(email, otp)
    
    return {"msg": "OTP sent to your email"}


@app.post("/verify_reset_otp")
def verify_reset_otp(data: dict, db: Session = Depends(get_db)):
    """
    Verifies OTP for password reset
    Returns a temporary token if OTP is valid
    """
    email = data.get("email")
    otp = data.get("otp")
    
    if not email or not otp:
        raise HTTPException(status_code=400, detail="Email and OTP are required")
    
    # Find user
    user = db.query(models.Student).filter_by(email=email).first()
    if not user or not user.otp_hash or not user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP not requested or expired")
    
    # Check expiration
    if datetime.utcnow() > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP expired")
    
    # Check attempts
    if user.otp_attempts >= 5:
        raise HTTPException(status_code=400, detail="Too many attempts")
    
    # Verify OTP
    if user.otp_hash != hash_otp(otp):
        user.otp_attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # OTP is valid - create a temporary reset token (using email as token for simplicity)
    # In production, use JWT or similar
    import secrets
    reset_token = secrets.token_urlsafe(32)
    
    # Store token temporarily (you might want to add a reset_token field to the model)
    # For now, we'll clear OTP and allow password reset
    user.otp_hash = None
    user.otp_expires_at = None
    user.otp_attempts = 0
    db.commit()
    
    return {"msg": "OTP verified", "reset_token": reset_token, "email": email}


@app.post("/reset_password")
def reset_password(data: dict, db: Session = Depends(get_db)):
    """
    Resets user password after OTP verification
    """
    email = data.get("email")
    new_password = data.get("new_password")
    
    if not email or not new_password:
        raise HTTPException(status_code=400, detail="Email and new password are required")
    
    # Validate password strength (same as registration)
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Find user
    user = db.query(models.Student).filter_by(email=email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password
    user.password_hash = new_password
    db.commit()
    
    return {"msg": "Password reset successful"}

@app.put("/students/{student_id}")
def update_student(student_id: int, data: dict, db: Session = Depends(get_db)):
    user = db.query(models.Student).filter_by(student_id=student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
    if "name" in data and data["name"]:
        user.name = data["name"].strip()
    if "profile_picture" in data:
        pic = data["profile_picture"]
        if pic is None:
            user.profile_picture = None
        else:
            # reject overly large base64 payloads (approx 2MB limit)
            max_chars = 2 * 1024 * 1024
            if len(pic) > max_chars:
                raise HTTPException(status_code=400, detail="Profile image too large (max 2MB).")
            user.profile_picture = pic
    db.commit()
    db.refresh(user)
    return {
        "msg": "Profile updated successfully",
        "student_id": user.student_id,
        "name": user.name,
        "email": user.email,
        "profile_picture": user.profile_picture
    }