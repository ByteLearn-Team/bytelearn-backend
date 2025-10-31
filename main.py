# Import the FastAPI class that helps create a web API easily in Python
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
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
import os
import re
import random
from sqlalchemy import or_

# Load any environment variables from a .env file (like DB passwords, etc)
load_dotenv()

# Make a FastAPI application object called 'app'
app = FastAPI()

# Add CORS middleware, which allows other websites (like your frontend) to access this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- include quiz router --
#from routers.quiz_router import router as quiz_router
#app.include_router(quiz_router)
# router is defined later in this file; registration moved to after its definition

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
    
    # UPDATED: Pass the db session and the user's name from the form
    await send_otp_email(student.email, otp, db=db, name=student.name)
    
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
        # PASS db to send_otp_email
        await send_otp_email(email, otp, db=db)
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
        # PASS db to send_otp_email
        await send_otp_email(email, otp, db=db)
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
async def generate(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Accept a student's doubt, persist it immediately, and schedule an asynchronous
    task to resolve the doubt using NCERT text + Groq (fallback to Flowise).
    Returns quickly with doubt_id so frontend can poll later if desired."""
    body = await request.json()
    prompt = body.get("prompt") or body.get("question") or body.get("input")
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing prompt")

    student_id = body.get("student_id")
    chapter_id = body.get("chapter_id")

    # create doubt record immediately so frontend receives an id to poll
    doubt = models.Doubt(
        doubt_question=prompt,
        created_at=datetime.utcnow(),
        student_id=student_id,
        chapter_id=chapter_id
    )
    try:
        db.add(doubt)
        db.commit()
        db.refresh(doubt)
        doubt_id = doubt.doubt_id
        print(f"Queued doubt {doubt_id} (student={student_id}, chapter={chapter_id})")
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Could not save doubt: {e}")

    # Background worker: resolve the doubt using NCERT context and Groq (fallback to Flowise)
    async def _process_doubt(doubt_id: int, prompt_text: str, student_id, chapter_id):
        # make a new DB session for background work
        db2 = SessionLocal()
        try:
            # Build NCERT context: prefer rows matching chapter_id, else fuzzy search in text
            q = db2.query(models.Ncert)
            if chapter_id:
                # Try to map chapter_id -> chapter_name, then search NCERT by name/text
                try:
                    chap = db2.query(models.Chapter).filter_by(chapter_id=chapter_id).first()
                    if chap and chap.chapter_name:
                        name = chap.chapter_name
                        q = q.filter(
                            or_(
                                models.Ncert.text_name.like(f"%{name}%"),
                                models.Ncert.ncert_text.like(f"%{name}%")
                            )
                        )
                    else:
                        # fallback to keyword search below if chapter not found
                        raise Exception("chapter not found")
                except Exception:
                    keywords = re.findall(r"\b[a-zA-Z]{4,}\b", prompt_text)
                    if keywords:
                        kw = keywords[:6]
                        filters = [models.Ncert.ncert_text.like(f"%{k}%") for k in kw]
                        q = q.filter(or_(*filters))
            else:
                # Search for some overlapping keywords from prompt
                keywords = re.findall(r"\b[a-zA-Z]{4,}\b", prompt_text)
                if keywords:
                    kw = keywords[:6]
                    # simple OR search on text_name and ncert_text
                    filters = [models.Ncert.ncert_text.like(f"%{k}%") for k in kw]
                    q = q.filter(or_(*filters))
            rows = q.limit(12).all()

            if not rows:
                # fallback grab some NCERT content
                rows = db2.query(models.Ncert).limit(20).all()

            context = "\\n\\n".join([r.ncert_text for r in rows if r.ncert_text])
            if len(context) > 15000:
                context = context[:15000]

            final_prompt = (
                "You are an educational assistant. Use the NCERT context below to answer the student's question. "
                f"If the context is not relevant, answer based on general knowledge.\n\nCONTEXT:\n{context}\n\nQUESTION:\n{prompt_text}\n\nAnswer concisely."
            )

            # Try Groq if configured
            groq_url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
            groq_key = os.getenv("GROQ_API_KEY")
            answer_text = None

            try:
                if groq_url and groq_key:
                    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        payload = {
                            "model": "llama3-8b-8192",
                            "messages": [
                                {"role": "system", "content": "You are a helpful assistant for students."},
                                {"role": "user", "content": final_prompt}
                            ]
                        }
                        resp = await client.post(groq_url, json=payload, headers=headers)
                        resp.raise_for_status()
                        j = resp.json()
                        # attempt common shapes
                        answer = None
                        if isinstance(j, dict):
                            answer = j.get("text") or j.get("output") or j.get("result") or j.get("answer")
                            if isinstance(answer, list) and answer:
                                first = answer[0]
                                if isinstance(first, dict) and first.get("text"):
                                    answer = first.get("text")
                            # Standard OpenAI/Groq chat completion format
                            elif j.get("choices") and isinstance(j["choices"], list) and j["choices"]:
                                message = j["choices"][0].get("message")
                                if message and isinstance(message, dict) and message.get("content"):
                                    answer = message["content"]
                        if not answer:
                            answer_text = str(j)
                        else:
                            answer_text = str(answer)

            except Exception as e:
                print(f"Error in background Groq call for doubt {doubt_id}: {e}")
                answer_text = f"Sorry, there was an error getting an answer from the AI assistant. Please try again later. (Error: {e})"

            # Persist the response linked to doubt
            try:
                resp_row = models.Response(
                    doubt_response = answer_text or "",
                    created_at = datetime.utcnow(),
                    doubt_id = doubt_id
                )
                db2.add(resp_row)
                db2.commit()
                print(f"Saved background response {getattr(resp_row, 'response_id', None)} for doubt {doubt_id}")
            except Exception as e:
                print(f"Failed to save response for doubt {doubt_id}: {e}")
                try:
                    db2.rollback()
                except Exception:
                    pass
        finally:
            db2.close()

    # schedule background processing (no await) and return queued response
    background_tasks.add_task(_process_doubt, doubt_id, prompt, student_id, chapter_id)
    return {"doubt_id": doubt_id, "status": "queued"}
    
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

    # UPDATED: Pass the db session (name will be looked up automatically)
    await send_otp_email(email, otp, db=db)

    return {"msg": "OTP sent to your email"}

# Endpoint to verify the OTP provided by the user
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

@app.post("/generate_quiz")
async def generate_quiz(request: Request, db: Session = Depends(get_db)):
    """
    Accepts JSON { "topic": "...", "num_questions": 5 }
    If num_questions <= 0 (or explicitly 0) -> generate maximum possible from NCERT text
    Returns JSON: { "quiz": [ { question, options: [...], correct_answer: "A", explanation } ] }
    """
    body = await request.json()
    topic = (body.get("topic") or "").strip()

    # parse requested count; treat 0 or negative as "generate maximum"
    try:
        num_q_raw = body.get("num_questions", None)
        if num_q_raw is None:
            num_questions = 5
        else:
            num_questions = int(num_q_raw)
    except Exception:
        num_questions = 5

    generate_max = False
    if num_questions <= 0:
        generate_max = True

    try:
        # Try to find relevant NCERT rows by topic; fallback to many rows if none found
        q = db.query(models.Ncert)
        if topic:
            q = q.filter(
                or_(
                    models.Ncert.text_name.like(f"%{topic}%"),
                    models.Ncert.ncert_text.like(f"%{topic}%")
                )
            )
        rows = q.limit(40).all()
        if not rows:
            rows = db.query(models.Ncert).limit(80).all()

        # combine text and split to sentences
        text = " ".join([r.ncert_text for r in rows if r.ncert_text])
        if not text or len(text) < 50:
            return {"quiz": [], "error": "Not enough NCERT content found for the requested topic."}

        # simple sentence split
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 30]
        random.shuffle(sentences)

        # build word pool for distractors
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text)
        words = [w for w in set(words) if len(w) >= 4]
        if not words:
            return {"quiz": [], "error": "Not enough vocabulary to create distractors."}

        quiz = []
        used_questions = set()
        for sent in sentences:
            # stop only if not generating max and we hit requested count
            if not generate_max and len(quiz) >= num_questions:
                break

            # pick candidate keyword (longest word in sentence not numeric)
            candidates = re.findall(r"\b[a-zA-Z]{4,}\b", sent)
            candidates = [c for c in candidates if c.lower() not in ("which","that","this","there","their","these","those")]
            if not candidates:
                continue
            keyword = max(candidates, key=len)
            if keyword.lower() in used_questions:
                continue
            used_questions.add(keyword.lower())

            # form question by replacing first occurrence of keyword with blank
            question_text = re.sub(re.escape(keyword), "____", sent, count=1, flags=re.IGNORECASE)

            # build distractors
            distractors = [w for w in words if w.lower() != keyword.lower()]
            random.shuffle(distractors)
            opts = [keyword] + distractors[:3]
            random.shuffle(opts)

            # format options as "A) ..." to keep frontend compatibility
            formatted_opts = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(opts)]
            correct_index = opts.index(keyword)
            correct_letter = chr(65 + correct_index)

            # simple explanation: include the original sentence as context
            explanation = f"The correct answer is '{keyword}'. Context: {sent}"

            quiz.append({
                "question": question_text,
                "options": formatted_opts,
                "correct_answer": correct_letter,   # letter e.g. "A"
                "explanation": explanation
            })

        # Return whatever we could build (if generate_max True, we attempted all sentences)
        return {"quiz": quiz, "topic": topic}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Quiz, QuizItem, Option
from datetime import datetime

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/generate_and_save_quiz")
async def generate_and_save_quiz(request: Request, db: Session = Depends(get_db)):
    """
    Accepts JSON:
      { "quiz": [ { question, options: [...], correct_answer: "A" | 0 | ... , explanation } ],
        "chapter_id": int,
        "student_id": int,
        "num_questions": int (optional)
      }
    Stores Quiz, QuizItem and Option rows and returns quiz_id and items.
    """
    try:
        body = await request.json()
        chapter_id = body.get("chapter_id")
        student_id = body.get("student_id")
        quiz_questions = body.get("quiz") or []

        if not quiz_questions or not isinstance(quiz_questions, list):
            raise HTTPException(status_code=400, detail="Missing or invalid 'quiz' array")

        # create quiz record
        quiz = Quiz(
            created_at=datetime.utcnow(),
            result_date=datetime.utcnow(),
            attempt_number=1,
            started_at=datetime.utcnow(),
            ended_at=datetime.utcnow(),
            score=0,
            chapter_id=chapter_id,
            student_id=student_id
        )
        db.add(quiz)
        db.flush()  # ensure quiz.quiz_id available

        saved_items = []
        for q in quiz_questions:
            item = QuizItem(
                question=q.get("question", ""),
                answer_explain=q.get("explanation", ""),
                quiz_id=quiz.quiz_id
            )
            db.add(item)
            db.flush()  # ensure item.question_id available

            opts = q.get("options", []) or []
            # support correct_answer as letter ("A") or index (0)
            corr = q.get("correct_answer", None)
            for idx, opt_text in enumerate(opts):
                # determine correctness string for Option.correct column
                is_correct = False
                if isinstance(corr, int):
                    is_correct = (idx == corr)
                elif isinstance(corr, str) and corr:
                    try:
                        is_correct = (corr.strip().upper() == chr(65 + idx))
                    except Exception:
                        is_correct = False
                elif corr is None:
                    # if no correct provided, assume first option
                    is_correct = (idx == 0)

                # Ensure option text fits DB column (models.Option.opt is String(35))
                safe_opt = (opt_text or "").strip()
                if len(safe_opt) > 35:
                    # Truncate rather than fail the whole request
                    safe_opt = safe_opt[:35]
                if not safe_opt:
                    safe_opt = "(no text)"
                option = Option(
                    opt=safe_opt,
                    correct="True" if is_correct else "False",
                    question_id=item.question_id
                )
                db.add(option)

            saved_items.append({"question_id": item.question_id, "question": item.question})

        db.commit()
        return {"quiz_id": quiz.quiz_id, "items": saved_items}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Minimal endpoint to update only the score column of an existing quiz row.
# Expects JSON: { "quiz_id": int, "score": number }
@router.post("/update_quiz_score")
async def update_quiz_score(data: dict, db: Session = Depends(get_db)):
    quiz_id = data.get("quiz_id")
    if not quiz_id:
        raise HTTPException(status_code=400, detail="Missing quiz_id")
    try:
        score_val = data.get("score")
        if score_val is None:
            raise HTTPException(status_code=400, detail="Missing score")
        score = float(score_val)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid score value")

    quiz = db.query(models.Quiz).filter_by(quiz_id=quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    quiz.score = score
    quiz.ended_at = datetime.utcnow()
    quiz.result_date = datetime.utcnow()
    db.commit()
    db.refresh(quiz)
    return {"msg": "quiz score updated", "quiz_id": quiz.quiz_id, "score": float(quiz.score)}

    # Endpoint to save/update quiz results. This does not create a new table; it uses existing
    # models (Quiz, QuizItem, Option). If `quiz_id` is provided it updates the score, otherwise
    # it creates a new Quiz record and optionally saves items/options when `quiz` array present.
@router.post("/save_quiz_result")
async def save_quiz_result(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        quiz_id = body.get("quiz_id")
        student_id = body.get("student_id")
        chapter_id = body.get("chapter_id")
        score = float(body.get("score", 0))
        correct = int(body.get("correct", 0))
        total = int(body.get("total", 0))
        quiz_questions = body.get("quiz") or []

        # If quiz_id provided, update existing quiz record
        if quiz_id:
            existing = db.query(models.Quiz).filter_by(quiz_id=quiz_id).first()
            if not existing:
                raise HTTPException(status_code=404, detail="Quiz not found")
            existing.score = score
            existing.ended_at = datetime.utcnow()
            existing.result_date = datetime.utcnow()
            existing.attempt_number = (existing.attempt_number or 0) + 1
            db.commit()
            db.refresh(existing)
            return {"msg": "quiz updated", "quiz_id": existing.quiz_id, "score": float(existing.score)}

        # Otherwise create a new quiz and (optionally) save items/options
        quiz = Quiz(
            created_at = datetime.utcnow(),
            result_date = datetime.utcnow(),
            attempt_number = 1,
            started_at = datetime.utcnow(),
            ended_at = datetime.utcnow(),
            score = score,
            chapter_id = chapter_id,
            student_id = student_id
        )
        db.add(quiz)
        db.flush()

        saved_items = []
        for q in quiz_questions:
            item = QuizItem(
                question = q.get("question", ""),
                answer_explain = q.get("explanation", "") or "",
                quiz_id = quiz.quiz_id
            )
            db.add(item)
            db.flush()

            opts = q.get("options", []) or []
            corr = q.get("correct_answer", None)
            for idx, opt_text in enumerate(opts):
                is_correct = False
                if isinstance(corr, int):
                    is_correct = (idx == corr)
                elif isinstance(corr, str) and corr:
                    try:
                        is_correct = (corr.strip().upper() == chr(65 + idx))
                    except Exception:
                        is_correct = False
                elif corr is None:
                    is_correct = (idx == 0)

                # Ensure option text fits DB column (models.Option.opt is String(35))
                safe_opt = (opt_text or "").strip()
                if len(safe_opt) > 35:
                    safe_opt = safe_opt[:35]
                if not safe_opt:
                    safe_opt = "(no text)"
                option = Option(
                    opt = safe_opt,
                    correct = "True" if is_correct else "False",
                    question_id = item.question_id
                )
                db.add(option)

            saved_items.append({"question_id": item.question_id, "question": item.question})

        db.commit()
        return {"msg": "quiz saved", "quiz_id": quiz.quiz_id, "score": score, "correct": correct, "total": total, "items": saved_items}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(router)


@app.get("/doubt/{doubt_id}")
def get_doubt(doubt_id: int, db: Session = Depends(get_db)):
    """Retrieve a doubt and its latest response so frontend can poll for answers."""
    doubt = db.query(models.Doubt).filter_by(doubt_id=doubt_id).first()
    if not doubt:
        raise HTTPException(status_code=404, detail="Doubt not found")
    resp = db.query(models.Response).filter_by(doubt_id=doubt_id).order_by(models.Response.created_at.desc()).first()
    return {
        "doubt_id": doubt.doubt_id,
        "question": doubt.doubt_question,
        "created_at": doubt.created_at.isoformat() if doubt.created_at else None,
        "response": resp.doubt_response if resp else None,
        "response_created_at": resp.created_at.isoformat() if resp and resp.created_at else None
    }