# Import the FastAPI class that helps create a web API easily in Python
from fastapi import FastAPI, Depends, HTTPException
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
    # Check if this email is already in the students table
    if db.query(crud.Student).filter_by(email=student.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    # Also check if in pending registrations (waiting for OTP)
    if db.query(models.PendingRegistration).filter_by(email=student.email).first():
        raise HTTPException(status_code=400, detail="Registration already pending for this email")
    # Generate and prepare OTP for this registration
    otp = generate_otp()
    otp_hash_val = hash_otp(otp)
    expires = datetime.utcnow() + timedelta(minutes=10)
    # Make a new pending registration record
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
    db.add(pending)         # Add to database
    db.commit()             # Save changes
    await send_otp_email(student.email, otp)     # Actually send the email with OTP
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
