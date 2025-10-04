from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
import crud, schemas
from fastapi.middleware.cors import CORSMiddleware
from otp_utils import generate_otp, hash_otp, send_otp_email
from datetime import datetime, timedelta
import asyncio
from sqlalchemy import and_
from dotenv import load_dotenv
import models
load_dotenv()

app = FastAPI()

# Add this after app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev, allow all. For prod, use your frontend URL.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Root route
@app.get("/")
def home():
    return {"msg": "ByteLearn backend connected to Aiven ✅"}

# GET all students
@app.get("/students", response_model=list[schemas.StudentOut])
def get_all_students(db: Session = Depends(get_db)):
    return crud.get_students(db)

# POST new student
@app.post("/students", response_model=schemas.StudentOut)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    return crud.create_student(db, student)

@app.post("/register")
async def register(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    # Check if email already exists in students or pending_registrations
    if db.query(crud.Student).filter_by(email=student.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(models.PendingRegistration).filter_by(email=student.email).first():
        raise HTTPException(status_code=400, detail="Registration already pending for this email")
    # Generate OTP
    otp = generate_otp()
    otp_hash_val = hash_otp(otp)
    expires = datetime.utcnow() + timedelta(minutes=10)
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

# GET all classes
@app.get("/classes", response_model=list[schemas.ClassOut])
def get_all_classes(db: Session = Depends(get_db)):
    return crud.get_classes(db)

# POST new class
@app.post("/classes", response_model=schemas.ClassOut)
def create_class(class_: schemas.ClassCreate, db: Session = Depends(get_db)):
    return crud.create_class(db, class_)

# GET all subjects
@app.get("/subjects", response_model=list[schemas.SubjectOut])
def get_all_subjects(db: Session = Depends(get_db)):
    return crud.get_subjects(db)

# POST new subject
@app.post("/subjects", response_model=schemas.SubjectOut)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    return crud.create_subject(db, subject)

# GET all chapters
@app.get("/chapters", response_model=list[schemas.ChapterOut])
def get_all_chapters(db: Session = Depends(get_db)):
    return crud.get_chapters(db)

# POST new chapter
@app.post("/chapters", response_model=schemas.ChapterOut)
def create_chapter(chapter: schemas.ChapterCreate, db: Session = Depends(get_db)):
    return crud.create_chapter(db, chapter)

# GET all summaries
@app.get("/summaries", response_model=list[schemas.SummaryOut])
def get_all_summaries(db: Session = Depends(get_db)):
    return crud.get_summaries(db)

# POST new summary
@app.post("/summaries", response_model=schemas.SummaryOut)
def create_summary(summary: schemas.SummaryCreate, db: Session = Depends(get_db)):
    return crud.create_summary(db, summary)

# GET all flashcards
@app.get("/flashcards", response_model=list[schemas.FlashcardOut])
def get_all_flashcards(db: Session = Depends(get_db)):
    return crud.get_flashcards(db)

# POST new flashcard
@app.post("/flashcards", response_model=schemas.FlashcardOut)
def create_flashcard(flashcard: schemas.FlashcardCreate, db: Session = Depends(get_db)):
    return crud.create_flashcard(db, flashcard)

# GET all images
@app.get("/images", response_model=list[schemas.ImageOut])
def get_all_images(db: Session = Depends(get_db)):
    return crud.get_images(db)

# POST new image
@app.post("/images", response_model=schemas.ImageOut)
def create_image(image: schemas.ImageCreate, db: Session = Depends(get_db)):
    return crud.create_image(db, image)

# GET all NCERT entries
@app.get("/ncert", response_model=list[schemas.NcertOut])
def get_all_ncerts(db: Session = Depends(get_db)):
    return crud.get_ncerts(db)

# POST new NCERT entry
@app.post("/ncert", response_model=schemas.NcertOut)
def create_ncert(ncert: schemas.NcertCreate, db: Session = Depends(get_db)):
    return crud.create_ncert(db, ncert)

@app.post("/login")
def login(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    password = data.get("password")
    user = db.query(crud.Student).filter_by(email=email).first()
    if not user or user.password_hash != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"student_id": user.student_id, "name": user.name, "email": user.email}

@app.post("/send_otp")
async def send_otp(data: dict, db: Session = Depends(get_db)):
    print("SEND_OTP CALLED", data)
    email = data.get("email")
    # Try pending_registrations first
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
    # Fallback: allow for students table (for legacy or future use)
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
    raise HTTPException(status_code=404, detail="User not found")

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
    # Create user in students table
    student = models.Student(
        name=pending.name,
        email=pending.email,
        password_hash=pending.password_hash,
        class_id=pending.class_id,
        is_verified=1
    )
    db.add(student)
    db.delete(pending)
    db.commit()
    return {"msg": "OTP verified"}