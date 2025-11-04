from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from database import SessionLocal
from fastapi.middleware.cors import CORSMiddleware
from otp_utils import generate_otp, hash_otp, send_otp_email
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, desc
from typing import List, Dict, Any
from dotenv import load_dotenv
import os
import json
import secrets
import httpx
import bcrypt
import models, schemas, crud
import re
import random


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def home():
    return {"msg": "BytLearn backend connected to Aiven ✅"}

@app.get("/students", response_model=list[schemas.StudentOut])
def get_all_students(db: Session = Depends(get_db)):
    return crud.get_students(db)

@app.post("/students", response_model=schemas.StudentOut)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    return crud.create_student(db, student)

@app.post("/register")
async def register(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    if db.query(crud.Student).filter_by(email=student.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    pending = db.query(models.PendingRegistration).filter_by(email=student.email).first()
    otp = generate_otp()
    otp_hash_val = hash_otp(otp)
    expires = datetime.utcnow() + timedelta(minutes=10)

    if pending:
        pending.otp_hash = otp_hash_val
        pending.otp_expires_at = expires
        pending.otp_attempts = 0
        pending.otp_last_sent_at = datetime.utcnow()
        pending.name = student.name or pending.name
        pending.password_hash = student.password_hash or pending.password_hash
        pending.class_id = student.class_id if student.class_id is not None else pending.class_id
        db.commit()
        await send_otp_email(student.email, otp, db=db, name=student.name)
        return {"msg": "OTP resent"}

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
    
    await send_otp_email(student.email, otp, db=db, name=student.name)
    
    return {"msg": "OTP sent"}

@app.get("/classes", response_model=list[schemas.ClassOut])
def get_all_classes(db: Session = Depends(get_db)):
    return crud.get_classes(db)

@app.post("/classes", response_model=schemas.ClassOut)
def create_class(class_: schemas.ClassCreate, db: Session = Depends(get_db)):
    return crud.create_class(db, class_)

@app.get("/subjects", response_model=list[schemas.SubjectOut])
def get_all_subjects(db: Session = Depends(get_db)):
    return crud.get_subjects(db)

@app.post("/subjects", response_model=schemas.SubjectOut)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    return crud.create_subject(db, subject)

@app.get("/chapters", response_model=list[schemas.ChapterOut])
def get_all_chapters(db: Session = Depends(get_db)):
    return crud.get_chapters(db)

@app.post("/chapters", response_model=schemas.ChapterOut)
def create_chapter(chapter: schemas.ChapterCreate, db: Session = Depends(get_db)):
    return crud.create_chapter(db, chapter)

@app.get("/summaries", response_model=list[schemas.SummaryOut])
def get_all_summaries(db: Session = Depends(get_db)):
    return crud.get_summaries(db)

@app.post("/summaries", response_model=schemas.SummaryOut)
def create_summary(summary: schemas.SummaryCreate, db: Session = Depends(get_db)):
    return crud.create_summary(db, summary)

@app.get("/flashcards", response_model=list[schemas.FlashcardOut])
def get_all_flashcards(db: Session = Depends(get_db)):
    return crud.get_flashcards(db)

@app.post("/flashcards", response_model=schemas.FlashcardOut)
def create_flashcard(flashcard: schemas.FlashcardCreate, db: Session = Depends(get_db)):
    return crud.create_flashcard(db, flashcard)

@app.get("/images", response_model=list[schemas.ImageOut])
def get_all_images(db: Session = Depends(get_db)):
    return crud.get_images(db)

@app.post("/images", response_model=schemas.ImageOut)
def create_image(image: schemas.ImageCreate, db: Session = Depends(get_db)):
    return crud.create_image(db, image)

@app.get("/ncert", response_model=list[schemas.NcertOut])
def get_all_ncerts(db: Session = Depends(get_db)):
    return crud.get_ncerts(db)

@app.post("/ncert", response_model=schemas.NcertOut)
def create_ncert(ncert: schemas.NcertCreate, db: Session = Depends(get_db)):
    return crud.create_ncert(db, ncert)

# -------------------------
# Password hashing utilities
# -------------------------
def hash_password(plain_password: str) -> str:
    """Hash a password using bcrypt."""
    if plain_password is None:
        return ""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str, db: Session = None, user: models.Student | None = None) -> bool:
    """
    Verify a password. Supports two modes:
    - standard bcrypt hashed_password (starts with $2)
    - legacy plaintext stored in DB (will re-hash and save if db+user provided)
    If plaintext is detected and matches, re-hash with bcrypt and update DB (one-time migration).
    """
    if not plain_password or not hashed_password:
        return False

    try:
        # If stored value looks like a bcrypt hash, verify normally
        if hashed_password.startswith("$2"):
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

        # Legacy: stored as plaintext (or other non-bcrypt). Compare directly.
        if plain_password == hashed_password:
            # If DB and user provided, upgrade to bcrypt hash immediately.
            if db is not None and user is not None:
                try:
                    user.password_hash = hash_password(plain_password)
                    db.commit()
                    print(f"🔁 Upgraded password for user {user.email} to bcrypt hash")
                except Exception as e:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                    print(f"⚠️ Failed to upgrade legacy password for {user.email}: {e}")
            return True

    except Exception as e:
        # Any error => treat as failed verification
        print(f"Error verifying password: {e}")
        return False

    return False

@app.post("/login")
def login(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    password = data.get("password")
    
    # Find user by email
    user = db.query(models.Student).filter_by(email=email).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # ✅ VERIFY PASSWORD USING BCRYPT (supports legacy plaintext and auto-upgrade)
    if not verify_password(password, user.password_hash or "", db=db, user=user):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "student_id": user.student_id, 
        "name": user.name, 
        "email": user.email
    }

@app.post("/send_otp")
async def send_otp(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    pending = db.query(models.PendingRegistration).filter_by(email=email).first()
    if pending:
        otp = generate_otp()
        pending.otp_hash = hash_otp(otp)
        pending.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        pending.otp_attempts = 0
        pending.otp_last_sent_at = datetime.utcnow()
        db.commit()
        await send_otp_email(email, otp, db=db)
        return {"msg": "OTP resent"}
    user = db.query(models.Student).filter_by(email=email).first()
    if user:
        otp = generate_otp()
        user.otp_hash = hash_otp(otp)
        user.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        user.otp_attempts = 0
        user.otp_last_sent_at = datetime.utcnow()
        db.commit()
        await send_otp_email(email, otp, db=db)
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

@app.post("/generate")
async def generate(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Accept a student's doubt, persist it immediately, and schedule an asynchronous
    task to resolve the doubt using NCERT text + Groq.
    Returns quickly with doubt_id so frontend can poll later."""
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

    # Background worker: resolve the doubt using NCERT context and Groq
    async def _process_doubt(doubt_id: int, prompt_text: str, student_id, chapter_id):
        # make a new DB session for background work
        db2 = SessionLocal()
        try:
            # Build NCERT context: prefer rows matching chapter_id, else fuzzy search in text
            q = db2.query(models.Ncert)
            if chapter_id:
                # Directly filter by chapter_id since the column now exists
                q = q.filter(models.Ncert.chapter_id == chapter_id)
            else:
                # Fallback to keyword search if no chapter_id is provided
                keywords = re.findall(r"\b[a-zA-Z]{4,}\b", prompt_text)
                if keywords:
                    kw = keywords[:6]
                    filters = [models.Ncert.ncert_text.like(f"%{k}%") for k in kw]
                    q = q.filter(or_(*filters))
            rows = q.limit(12).all()

            if not rows:
                rows = db2.query(models.Ncert).limit(20).all()

            context = "\n\n".join([r.ncert_text for r in rows if r.ncert_text])
            if len(context) > 15000:
                context = context[:15000]

            system_prompt = (
    "You are an educational assistant specializing in NCERT curriculum content. Your primary role is to help students learn directly from their textbooks.\n\n"
    "RESPONSE GUIDELINES:\n\n"
    "1. GREETINGS & GENERAL CONVERSATION:\n"
    "   - Respond naturally to greetings (hi, hello, how are you, good morning, etc.)\n"
    "   - Handle common courtesy exchanges warmly and briefly\n"
    "   - Answer general common-sense questions politely\n\n"
    "2. NCERT CONTENT QUESTIONS (STRICT MODE):\n"
    "   - ALWAYS answer ONLY from the provided NCERT context for chapter-related questions\n"
    "   - Use EXACT lines and phrases from the context whenever possible\n"
    "   - Quote or paraphrase directly from the textbook content\n"
    "   - Do NOT add external information to NCERT-based answers\n"
    "   - Stay faithful to the textbook's explanations, definitions, and examples\n"
    "   - Maintain the same terminology and explanation style as the NCERT text\n\n"
    "3. WHEN CONTEXT IS NOT SUFFICIENT:\n"
    "   - If the question is educational but not covered in the provided context, respond with:\n"
    "     'This is not part of the current chapter content. However, as part of general knowledge: [provide answer]'\n"
    "   - Clearly distinguish between NCERT content and general knowledge\n"
    "   - For follow-up questions beyond the chapter scope, use the same disclaimer\n\n"
    "4. STYLE:\n"
    "   - Be concise and precise\n"
    "   - For NCERT answers: use exact textbook terminology\n"
    "   - For general knowledge: keep it simple and student-friendly\n"
    "   - Be helpful and supportive throughout\n\n"
    "PRIORITY: Always check the context first. If the answer is in the NCERT context, use ONLY that. If not, clearly state it's general knowledge before answering."
)
            user_prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{prompt_text}"

            # Try Groq if configured
            groq_url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
            groq_key = os.getenv("GROQ_API_KEY")
            print(f"DEBUG: Using Groq Key: {groq_key[:5]}...{groq_key[-4:] if groq_key else 'None'}")

            answer_text = None

            try:
                if groq_url and groq_key:
                    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        payload = {
                            "model": "llama-3.3-70b-versatile",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
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
                            # If parsing fails, don't save the raw JSON. Use a fallback message.
                            print(f"Could not parse answer from Groq response: {j}")
                            answer_text = "Sorry, the AI returned an unexpected response format."
                        else:
                            answer_text = str(answer)

            except Exception as e:
                # Add this block to print the detailed error message from Groq's server
                if isinstance(e, httpx.HTTPStatusError):
                    print(f"Groq API response error: {e.response.status_code} - {e.response.text}")
                
                print(f"Error in background Groq call for doubt {doubt_id}: {e}")
                answer_text = f"Sorry, there was an error getting an answer from the AI assistant. Please try again later."

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
            
            # ✅ NEW: Update progress after doubt is answered
            try:
                if student_id and chapter_id:
                    # Check if progress exists for this student-chapter
                    progress = db2.query(models.Progress).filter(
                        models.Progress.student_id == student_id,
                        models.Progress.chapter_id == chapter_id
                    ).first()
                    
                    if progress:
                        # Update existing progress with latest doubt_id
                        progress.doubt_id = doubt_id
                        # Optionally update strong area to show engagement
                        if not progress.strong_area or progress.strong_area == "Continue practicing":
                            progress.strong_area = "Active learner - asking questions"
                        db2.commit()
                        print(f"✅ Updated progress with doubt {doubt_id} for chapter {chapter_id}")
                    else:
                        # Create new progress record focused on doubt engagement
                        chapter = db2.query(models.Chapter).filter_by(chapter_id=chapter_id).first()
                        chapter_name = chapter.chapter_name if chapter else f"Chapter {chapter_id}"
                        
                        new_progress = models.Progress(
                            student_id=student_id,
                            chapter_id=chapter_id,
                            doubt_id=doubt_id,
                            quiz_id=None,
                            avg_time=0.0,
                            accuracy=0.0,
                            weak_area=f"{chapter_name}: Start with quizzes to identify weak areas",
                            strong_area="Active learner - asking questions"
                        )
                        db2.add(new_progress)
                        db2.commit()
                        print(f"✅ Created new progress record with doubt {doubt_id}")
            except Exception as e:
                print(f"⚠️ Failed to update progress for doubt {doubt_id}: {e}")
                try:
                    db2.rollback()
                except Exception:
                    pass
                    
        finally:
            db2.close()

    # schedule background processing (no await) and return queued response
    background_tasks.add_task(_process_doubt, doubt_id, prompt, student_id, chapter_id)
    return {"doubt_id": doubt_id, "status": "queued"}
    
@app.post("/forgot_password")
async def forgot_password(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user = db.query(models.Student).filter_by(email=email).first()
    if not user:
        raise HTTPException(status_code=404, detail="If this email exists, an OTP has been sent")
    
    otp = generate_otp()
    otp_hash_val = hash_otp(otp)
    expires = datetime.utcnow() + timedelta(minutes=10)
    
    user.otp_hash = otp_hash_val
    user.otp_expires_at = expires
    user.otp_attempts = 0
    user.otp_last_sent_at = datetime.utcnow()
    db.commit()

    await send_otp_email(email, otp, db=db)

    return {"msg": "OTP sent to your email"}

@app.post("/verify_reset_otp")
def verify_reset_otp(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    otp = data.get("otp")
    
    if not email or not otp:
        raise HTTPException(status_code=400, detail="Email and OTP are required")
    
    user = db.query(models.Student).filter_by(email=email).first()
    if not user or not user.otp_hash or not user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP not requested or expired")
    
    if datetime.utcnow() > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP expired")
    
    if user.otp_attempts >= 5:
        raise HTTPException(status_code=400, detail="Too many attempts")
    
    if user.otp_hash != hash_otp(otp):
        user.otp_attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    import secrets
    reset_token = secrets.token_urlsafe(32)
    
    user.otp_hash = None
    user.otp_expires_at = None
    user.otp_attempts = 0
    db.commit()
    
    return {"msg": "OTP verified", "reset_token": reset_token, "email": email}

@app.post("/reset_password")
def reset_password(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    new_password = data.get("new_password")
    
    if not email or not new_password:
        raise HTTPException(status_code=400, detail="Email and new password are required")
    
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    user = db.query(models.Student).filter_by(email=email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
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
    """Generate NEET-pattern quiz questions using NCERT context + Groq AI"""
    body = await request.json()
    
    try:
        chapter_id = body.get("chapter_id")
        num_questions = body.get("num_questions", 10)
        
        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required")
        
        # Fetch NCERT content for the chapter
        q = db.query(models.Ncert)
        q = q.filter(models.Ncert.chapter_id == chapter_id)
        rows = q.limit(40).all()
        
        if not rows:
            # Fallback to general NCERT content
            rows = db.query(models.Ncert).limit(80).all()
        
        # Build context from NCERT text
        context = "\n\n".join([r.ncert_text for r in rows if r.ncert_text])
        if len(context) > 20000:
            context = context[:20000]
        
        if not context or len(context) < 100:
            return {"quiz": [], "error": "Not enough NCERT content found for quiz generation."}
        
        # Prepare Groq API request
        groq_url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
        groq_key = os.getenv("GROQ_API_KEY")
        
        if not groq_url or not groq_key:
            raise HTTPException(status_code=500, detail="Groq API not configured")
        
        # System prompt for NEET-pattern quiz generation
        system_prompt = f"""You are an expert NEET Biology question generator with deep knowledge of NCERT curriculum and NEET exam patterns.

Create {num_questions} high-quality multiple-choice questions based STRICTLY on the provided NCERT content from the specified chapter.

CRITICAL: AVOID REPETITION
- Do NOT generate questions similar to previously generated questions from this chapter
- Vary specific topics, concepts, and angles being tested
- If a concept was tested before, approach it from a completely different perspective
- Focus on untested subsections, examples, or applications from the chapter

STRICT REQUIREMENTS:

1. CONTENT ALIGNMENT:
   - Every question MUST be derived directly from the provided NCERT chapter content below
   - Do NOT use external knowledge or information beyond the given NCERT text
   - Questions should cover key concepts, definitions, processes, and examples mentioned in the chapter
   - Ensure questions span across different sections of the chapter for comprehensive coverage

2. NEET DIFFICULTY STANDARD:
   - Questions must match authentic NEET exam difficulty (moderate to hard)
   - Include a mix of: 40% factual recall, 35% application-based, 25% conceptual understanding
   - Avoid overly easy or trivial questions that test only surface-level memorization
   - Create questions that require careful reading and critical thinking

3. QUESTION STRUCTURE:
   - Each question must have EXACTLY 4 options labeled A, B, C, D
   - Options should be similar in length (within 2-3 words difference)
   - All options must be grammatically parallel and stylistically consistent
   - Avoid patterns like "all of the above" or "none of the above" unless absolutely necessary

4. OPTION QUALITY (CRITICAL):
   - Correct answer must be definitively correct based on NCERT content
   - All 3 distractors must be highly plausible and scientifically reasonable
   - Distractors should be based on:
     * Common student misconceptions
     * Related but incorrect concepts from the same chapter
     * Partial truths or incomplete statements
     * Similar-sounding terms or processes
   - Avoid obviously wrong answers (like joke options or absurd statements)
   - Make the student think carefully between 2-3 options

5. SCIENTIFIC RIGOR:
   - Use precise scientific terminology as given in NCERT
   - Maintain taxonomic accuracy (correct genus, species, family names)
   - Include proper units, values, and ranges where applicable
   - Use standard nomenclature and conventions

6. EXPLANATION REQUIREMENTS:
   - Start with NCERT reference: "According to NCERT [Chapter Name]..."
   - Quote exact relevant lines from NCERT that support the correct answer
   - Explain clearly WHY the correct answer is right
   - Explain WHY each distractor is incorrect with specific reasoning
   - Connect explanation back to the chapter's key concepts
   - Keep explanations comprehensive but concise (4-6 sentences)

7. QUESTION DIVERSITY:
   - Vary question types: definitions, functions, examples, comparisons, sequences, exceptions, processes
   - Cover different topics within the chapter evenly
   - Alternate question stems: "Which of the following...", "Identify the correct...", "What is the role of...", "During which process..."
   - Include statement-based questions (Statement I and II format) when appropriate
   - Test relationships between concepts, not just isolated facts

FORMAT YOUR RESPONSE AS VALID JSON ONLY:
{{
  "questions": [
    {{
      "question": "Complete question text here",
      "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
      "correct_answer": "A",
      "explanation": "According to NCERT [Chapter], '[exact quote from NCERT]'. This establishes that [explanation]. Option B is incorrect because [reason]. Option C is incorrect because [reason]. Option D is incorrect because [reason].",
      "topic_tags": ["main topic", "subtopic"]
    }}
  ]
}}

NCERT CONTEXT:
{context}

Generate exactly {num_questions} UNIQUE questions following all requirements above. Return ONLY valid JSON, no additional text before or after."""
        
        # Call Groq API
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(groq_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # Extract AI response
            ai_response = None
            if result.get("choices") and isinstance(result["choices"], list) and result["choices"]:
                message = result["choices"][0].get("message")
                if message and isinstance(message, dict) and message.get("content"):
                    ai_response = message["content"]
            
            if not ai_response:
                raise HTTPException(status_code=500, detail="Invalid response from AI")
            
            # Parse JSON response
            import json
            
            # Try to extract JSON from response (in case there's extra text)
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise HTTPException(status_code=500, detail="AI did not return valid JSON")
            
            json_str = ai_response[json_start:json_end]
            quiz_data = json.loads(json_str)
            
            # Validate and format questions
            questions = quiz_data.get("questions", [])
            
            if not questions:
                raise HTTPException(status_code=500, detail="No questions generated")
            
            # Format for frontend
            formatted_quiz = []
            for q in questions[:num_questions]:  # Ensure we don't exceed requested number
                formatted_quiz.append({
                    "question": q.get("question", ""),
                    "options": q.get("options", [])[:4],  # Ensure exactly 4 options
                    "correct_answer": q.get("correct_answer", "A"),
                    "explanation": q.get("explanation", "")
                })
            
            return {"quiz": formatted_quiz, "topic": f"Chapter {chapter_id}"}
            
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except httpx.HTTPStatusError as e:
        print(f"Groq API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=500, detail="AI service error")
    except Exception as e:
        print(f"Quiz generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter
router = APIRouter()

@router.post("/generate_and_save_quiz")
async def generate_and_save_quiz(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        chapter_id = body.get("chapter_id")
        student_id = body.get("student_id")
        quiz_questions = body.get("quiz") or []

        if not quiz_questions or not isinstance(quiz_questions, list):
            raise HTTPException(status_code=400, detail="Missing or invalid 'quiz' array")

        quiz = models.Quiz(
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
        db.flush()

        saved_items = []
        for q in quiz_questions:
            item = models.QuizItem(
                question=q.get("question", ""),
                answer_explain=q.get("explanation", ""),
                quiz_id=quiz.quiz_id
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

                safe_opt = (opt_text or "").strip()
                if len(safe_opt) > 35:
                    safe_opt = safe_opt[:35]
                if not safe_opt:
                    safe_opt = "(no text)"
                option = models.Option(
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

@router.post("/save_quiz_result")
async def save_quiz_result(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        quiz_id = body.get("quiz_id")
        student_id = body.get("student_id")
        chapter_id = body.get("chapter_id")
        quiz_questions = body.get("quiz") or []
        user_answers = body.get("user_answers")
        total_time_seconds = body.get("total_time_seconds", 0)

        # Calculate score on the backend
        score = 0
        correct_count = 0
        total_questions = len(quiz_questions)

        if total_questions > 0 and user_answers and len(user_answers) == total_questions:
            for i, q in enumerate(quiz_questions):
                correct_answer_letter = q.get("correct_answer", "").strip().upper()
                user_answer_index = user_answers[i]

                if user_answer_index is not None:
                    user_answer_letter = chr(65 + user_answer_index)
                    if user_answer_letter == correct_answer_letter:
                        correct_count += 1
            
            score = round((correct_count / total_questions) * 100, 2)

        if quiz_id:
            existing = db.query(models.Quiz).filter_by(quiz_id=quiz_id).first()
            if not existing:
                raise HTTPException(status_code=404, detail="Quiz not found")
            existing.score = score
            existing.ended_at = datetime.utcnow()
            existing.result_date = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            
            # UPDATE PROGRESS after quiz completion
            update_student_progress(
                student_id=student_id,
                chapter_id=chapter_id,
                quiz_id=existing.quiz_id,
                db=db
            )
            
            return {"msg": "quiz updated", "quiz_id": existing.quiz_id, "score": float(existing.score)}

        ended_at_time = datetime.utcnow()
        started_at_time = ended_at_time - timedelta(seconds=total_time_seconds)

        quiz = models.Quiz(
            created_at = started_at_time,
            result_date = ended_at_time,
            attempt_number = 1,
            started_at = started_at_time,
            ended_at = ended_at_time,
            score = score,
            chapter_id = chapter_id,
            student_id = student_id
        )
        db.add(quiz)
        db.flush()

        saved_items = []
        for q in quiz_questions:
            item = models.QuizItem(
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

                safe_opt = (opt_text or "").strip()
                if len(safe_opt) > 35:
                    safe_opt = safe_opt[:35]
                if not safe_opt:
                    safe_opt = "(no text)"
                option = models.Option(
                    opt = safe_opt,
                    correct = "True" if is_correct else "False",
                    question_id = item.question_id
                )
                db.add(option)

            saved_items.append({"question_id": item.question_id, "question": item.question})

        db.commit()
        
        # UPDATE PROGRESS after new quiz is saved
        update_student_progress(
            student_id=student_id,
            chapter_id=chapter_id,
            quiz_id=quiz.quiz_id,
            db=db
        )
        
        return {"msg": "quiz saved", "quiz_id": quiz.quiz_id, "score": score, "correct": correct_count, "total": total_questions, "items": saved_items}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(router)

@app.get("/doubt/{doubt_id}")
def get_doubt_details(doubt_id: int, db: Session = Depends(get_db)):
    """Retrieve a doubt and its latest response so frontend can poll for answers."""
    doubt = db.query(models.Doubt).filter_by(doubt_id=doubt_id).first()
    if not doubt:
        raise HTTPException(status_code=404, detail="Doubt not found")
    resp = db.query(models.Response).filter_by(doubt_id=doubt_id).order_by(models.Response.created_at.desc()).first()
    response_data = {
        "doubt_id": doubt.doubt_id,
        "question": doubt.doubt_question,
        "created_at": doubt.created_at.isoformat() if doubt.created_at else None,
        "response": resp.doubt_response if resp else None,
        "response_created_at": resp.created_at.isoformat() if resp and resp.created_at else None
    }

    return response_data

# ✅ UPDATED FUNCTION: Update student progress after quiz completion
def update_student_progress(student_id: int, chapter_id: int, quiz_id: int = None, 
                           doubt_id: int = None, db: Session = None):
    """
    Update or create progress record for a student after quiz or doubt activity.
    Calculates accuracy, avg_time, and identifies strong/weak areas.
    Strong areas: >= 80% accuracy
    Weak areas: < 80% accuracy
    
    ✅ UPDATED: Now updates existing records instead of creating duplicates
    """
    try:
        # Get chapter name for better messaging
        chapter = db.query(models.Chapter).filter_by(chapter_id=chapter_id).first()
        chapter_name = chapter.chapter_name if chapter else f"Chapter {chapter_id}"
        
        # Get all quizzes for this student and chapter
        quizzes = db.query(models.Quiz).filter(
            models.Quiz.student_id == student_id,
            models.Quiz.chapter_id == chapter_id
        ).all()
        
        if not quizzes:
            return
        
        # Calculate accuracy (average score)
        scores = [float(q.score) for q in quizzes if q.score is not None]
        accuracy = sum(scores) / len(scores) if scores else 0
        
        # Calculate average time per quiz
        times = []
        for q in quizzes:
            if q.started_at and q.ended_at:
                duration = (q.ended_at - q.started_at).total_seconds()
                times.append(duration)
        avg_time = sum(times) / len(times) if times else 0
        
        # Identify weak and strong areas based on 80% threshold
        if accuracy >= 80:
            # Strong area
            strong_area = f"{chapter_name}: Excellent performance ({accuracy:.1f}%)"
            weak_area = ""  # No weakness if performing well
        elif accuracy >= 60:
            # Moderate performance
            strong_area = f"{chapter_name}: Good understanding of basics"
            weak_area = f"{chapter_name}: Some advanced topics need revision ({accuracy:.1f}%)"
        else:
            # Weak area
            strong_area = ""  # No strength if performing poorly
            weak_area = f"{chapter_name}: Needs significant revision ({accuracy:.1f}%)"
        
        # ✅ Check if progress record exists for this student-chapter combination
        progress = db.query(models.Progress).filter(
            models.Progress.student_id == student_id,
            models.Progress.chapter_id == chapter_id
        ).first()
        
        if progress:
            # ✅ UPDATE existing record (prevents duplicates)
            progress.avg_time = round(avg_time, 2)
            progress.accuracy = round(accuracy, 2)
            progress.weak_area = weak_area or "No major weak areas"
            progress.strong_area = strong_area or "Continue practicing"
            if quiz_id:
                progress.quiz_id = quiz_id
            if doubt_id:
                progress.doubt_id = doubt_id
            
            print(f"✅ UPDATED progress for student {student_id}, chapter {chapter_id}: {accuracy:.1f}% accuracy")
        else:
            # ✅ Create NEW progress record (only if none exists)
            progress = models.Progress(
                student_id=student_id,
                chapter_id=chapter_id,
                quiz_id=quiz_id,
                doubt_id=doubt_id,
                avg_time=round(avg_time, 2),
                accuracy=round(accuracy, 2),
                weak_area=weak_area or "No major weak areas",
                strong_area=strong_area or "Continue practicing"
            )
            db.add(progress)
            print(f"✅ CREATED new progress for student {student_id}, chapter {chapter_id}: {accuracy:.1f}% accuracy")
        
        db.commit()
        
    except Exception as e:
        print(f"❌ Error updating progress: {e}")
        try:
            db.rollback()
        except:
            pass

@app.get("/students/{student_id}/statistics")
def get_student_statistics(student_id: int, db: Session = Depends(get_db)):
    """
    Get comprehensive statistics for a student using BOTH quizzes data AND progress table.
    Progress table provides pre-calculated strong/weak areas based on 80% threshold.
    """
    
    # Check if student exists
    student = db.query(models.Student).filter_by(student_id=student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get all quizzes for this student
    quizzes = db.query(models.Quiz).filter_by(student_id=student_id).all()
    
    # Get all doubts for this student
    doubts = db.query(models.Doubt).filter_by(student_id=student_id).all()
    
    # Calculate basic quiz statistics
    quiz_count = len(quizzes)
    if quiz_count > 0:
        scores = [float(q.score) for q in quizzes if q.score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        best_score = max(scores) if scores else 0
        
        # Calculate average time per quiz (in seconds)
        times = []
        for q in quizzes:
            if q.started_at and q.ended_at:
                duration = (q.ended_at - q.started_at).total_seconds()
                times.append(duration)
        
        avg_time = sum(times) / len(times) if times else 0
        fastest_time = min(times) if times else 0
    else:
        avg_score = 0
        best_score = 0
        avg_time = 0
        fastest_time = 0
    
    # Calculate doubt resolution rate
    doubt_count = len(doubts)
    resolved_doubts = db.query(models.Doubt).filter(
        models.Doubt.student_id == student_id,
        models.Doubt.doubt_id.in_(
            db.query(models.Response.doubt_id).distinct()
        )
    ).count()
    
    doubt_resolution_rate = (resolved_doubts / doubt_count * 100) if doubt_count > 0 else 0
    
    # Calculate study streak
    study_streak = calculate_study_streak(student_id, db)
    
    # Get topic-wise performance (from quizzes)
    topic_performance = get_topic_performance(student_id, db)
    
    # Get weekly trend
    weekly_trend = get_weekly_trend(student_id, db)
    
    # *** NEW: Get strong and weak areas from PROGRESS TABLE ***
    strong_areas, weak_areas = get_areas_from_progress(student_id, db)
    
    # Get recent activity
    recent_activity = get_recent_activity(student_id, db)
    
    # Generate personalized suggestions based on progress data
    suggestions = generate_suggestions_from_progress(student_id, avg_time, db)
    
    return {
        "student_id": student_id,
        "summary": {
            "study_streak": study_streak,
            "average_score": round(avg_score, 1),
            "avg_quiz_time": round(avg_time, 0),
            "doubt_resolution_rate": round(doubt_resolution_rate, 0)
        },
        "performance": {
            "quizzes_completed": quiz_count,
            "average_score": round(avg_score, 1),
            "best_score": round(best_score, 1),
            "avg_time_per_quiz": round(avg_time, 0),
            "fastest_completion": round(fastest_time, 0)
        },
        "topic_performance": topic_performance,
        "weekly_trend": weekly_trend,
        "strong_areas": strong_areas,
        "weak_areas": weak_areas,
        "recent_activity": recent_activity,
        "suggestions": suggestions
    }


def calculate_study_streak(student_id: int, db: Session) -> int:
    """Calculate consecutive days of study activity"""
    # Get all quiz dates
    quiz_dates = db.query(
        func.date(models.Quiz.created_at).label('date')
    ).filter(
        models.Quiz.student_id == student_id
    ).distinct().order_by(desc('date')).all()
    
    if not quiz_dates:
        return 0
    
    # Convert to list of dates
    dates = [d[0] for d in quiz_dates]
    
    # Calculate streak from today
    today = datetime.now().date()
    streak = 0
    current_date = today
    
    for date in dates:
        if date == current_date:
            streak += 1
            current_date -= timedelta(days=1)
        elif date < current_date:
            break
    
    return streak


def get_topic_performance(student_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Get performance breakdown for the 6 most recently quizzed chapters/topics.
    """
    
    # 1. Find the 6 most recent unique chapters the student has taken a quiz in.
    #    This subquery finds the latest quiz timestamp for each chapter for the student.
    latest_quiz_subquery = db.query(
        models.Quiz.chapter_id,
        func.max(models.Quiz.created_at).label('last_quiz_date')
    ).filter(
        models.Quiz.student_id == student_id
    ).group_by(
        models.Quiz.chapter_id
    ).subquery('latest_quiz')

    # 2. Join this with the quizzes and chapters table to get avg scores and names,
    #    ordering by the most recent activity and limiting to 6.
    results = db.query(
        models.Chapter.chapter_id,
        models.Chapter.chapter_name,
        func.avg(models.Quiz.score).label('avg_score')
    ).join(
        latest_quiz_subquery, models.Chapter.chapter_id == latest_quiz_subquery.c.chapter_id
    ).join(
        models.Quiz, 
        and_(
            models.Quiz.chapter_id == models.Chapter.chapter_id,
            models.Quiz.student_id == student_id
        )
    ).group_by(
        models.Chapter.chapter_id,
        models.Chapter.chapter_name,
        latest_quiz_subquery.c.last_quiz_date
    ).order_by(
        desc(latest_quiz_subquery.c.last_quiz_date)
    ).limit(6).all()

    if not results:
        # If there are no results, return an empty list.
        # The frontend will show a "start taking quizzes" message.
        return []

    # 3. Build the final data structure.
    topic_data = []
    for chapter_id, chapter_name, avg_score in results:
        # Create a shorter name for the chart label that can wrap
        words = chapter_name.replace(" and ", " & ").split()
        short_name = " ".join(words[:3]) if len(words) > 3 else chapter_name

        topic_data.append({
            "name": short_name,
            "full_name": chapter_name,
            "score": round(float(avg_score), 1) if avg_score is not None else 0,
        })
    
    return topic_data


def get_weekly_trend(student_id: int, db: Session) -> List[Dict[str, Any]]:
    """Get performance trend for last 7 days"""
    today = datetime.now().date()
    weekly_data = []
    
    for i in range(6, -1, -1):  # Last 7 days
        date = today - timedelta(days=i)
        
        # Get average score for that day
        day_quizzes = db.query(
            func.avg(models.Quiz.score).label('avg_score')
        ).filter(
            models.Quiz.student_id == student_id,
            func.date(models.Quiz.created_at) == date
        ).first()
        
        avg_score = float(day_quizzes.avg_score) if day_quizzes.avg_score else 0
        
        weekly_data.append({
            "day": date.strftime('%a'),  # Mon, Tue, etc.
            "date": date.isoformat(),
            "score": round(avg_score, 1)
        })
    
    return weekly_data


# ✅ UPDATED FUNCTION: Get strong and weak areas from Progress table (NO DUPLICATES)
def get_areas_from_progress(student_id: int, db: Session) -> tuple:
    """
    Retrieve strong and weak areas from the Progress table.
    Strong areas: chapters with >= 80% accuracy
    Weak areas: chapters with < 80% accuracy
    
    ✅ UPDATED: Now returns only ONE record per chapter (latest/best)
    """
    
    # ✅ Get ONLY ONE progress record per chapter (the one with highest accuracy)
    # This prevents duplicate chapters in the UI
    subquery = db.query(
        models.Progress.chapter_id,
        func.max(models.Progress.accuracy).label('max_accuracy')
    ).filter(
        models.Progress.student_id == student_id
    ).group_by(
        models.Progress.chapter_id
    ).subquery()
    
    # Join to get the actual progress records with highest accuracy per chapter
    progress_records = db.query(models.Progress).join(
        subquery,
        and_(
            models.Progress.chapter_id == subquery.c.chapter_id,
            models.Progress.accuracy == subquery.c.max_accuracy,
            models.Progress.student_id == student_id
        )
    ).order_by(desc(models.Progress.accuracy)).all()
    
    if not progress_records:
        return [], []
    
    strong_areas = []
    weak_areas = []
    
    # ✅ Track chapters we've already added to avoid duplicates
    seen_chapters = set()
    
    for progress in progress_records:
        # ✅ Skip if we've already processed this chapter
        if progress.chapter_id in seen_chapters:
            continue
        
        seen_chapters.add(progress.chapter_id)
        
        accuracy = float(progress.accuracy) if progress.accuracy else 0
        
        # Get chapter name
        chapter = db.query(models.Chapter).filter_by(
            chapter_id=progress.chapter_id
        ).first()
        chapter_name = chapter.chapter_name if chapter else f"Chapter {progress.chapter_id}"
        
        # Strong area: >= 80%
        if accuracy >= 80:
            if progress.strong_area and progress.strong_area != "Continue practicing":
        # Extract just the detail part after the colon
                if ": " in progress.strong_area:
                    detail = progress.strong_area.split(": ", 1)[1]
                else:
                    detail = progress.strong_area
            else:
                detail = f"Excellent performance ({accuracy:.1f}%)"
            strong_areas.append({
                "topic": chapter_name,
                "detail": detail,
                "accuracy": accuracy
            })
        
        # Weak area: < 80%
        elif accuracy > 0:  # Only include if there's actual data
            if progress.weak_area and progress.weak_area != "No major weak areas":
        # Extract just the detail part after the colon
                if ": " in progress.weak_area:
                    detail = progress.weak_area.split(": ", 1)[1]
                else:
                    detail = progress.weak_area
            else:
                detail = f"Needs improvement ({accuracy:.1f}%)"
            weak_areas.append({
                "topic": chapter_name,
                "detail": detail,
                "accuracy": accuracy
            })
    
    # Return top 3 strong and weak areas
    return strong_areas[:3], weak_areas[:3]


def get_recent_activity(student_id: int, db: Session) -> List[Dict[str, Any]]:
    """Get recent quizzes and activity"""
    recent_quizzes = db.query(models.Quiz).filter(
        models.Quiz.student_id == student_id
    ).order_by(
        desc(models.Quiz.created_at)
    ).limit(5).all()
    
    activities = []
    for quiz in recent_quizzes:
        # Get chapter name
        chapter = db.query(models.Chapter).filter_by(
            chapter_id=quiz.chapter_id
        ).first()
        
        # ✅ FIXED: Return actual ISO date string instead of "Today" or "X days ago"
        # Frontend will handle the date formatting
        date_str = quiz.created_at.date().isoformat() if quiz.created_at else None
        
        # Calculate time taken
        if quiz.started_at and quiz.ended_at:
            duration = (quiz.ended_at - quiz.started_at).total_seconds()
            time_str = f"{int(duration)}s"
        else:
            time_str = "N/A"
        
        activities.append({
            "activity": f"Quiz: {chapter.chapter_name if chapter else 'Unknown'}",
            "date": date_str,  # ✅ Now returns "2024-11-03" format
            "score": round(float(quiz.score), 0) if quiz.score else None,
            "time": time_str
        })
    
    return activities

# NEW FUNCTION: Generate suggestions based on progress data
def generate_suggestions_from_progress(student_id: int, avg_time: float, 
                                       db: Session) -> List[Dict[str, str]]:
    """
    Generate personalized study suggestions based on progress table data.
    """
    suggestions = []
    
    # Get weak areas from progress table
    progress_records = db.query(models.Progress).filter(
        models.Progress.student_id == student_id,
        models.Progress.accuracy < 80
    ).order_by(models.Progress.accuracy).limit(2).all()
    
    # Suggestions based on weak areas
    for progress in progress_records:
        chapter = db.query(models.Chapter).filter_by(
            chapter_id=progress.chapter_id
        ).first()
        chapter_name = chapter.chapter_name if chapter else f"Chapter {progress.chapter_id}"
        
        suggestions.append({
            "title": f"Focus on {chapter_name}",
            "detail": f"Current accuracy: {float(progress.accuracy):.1f}%. Practice 10 MCQs daily and review concepts thoroughly."
        })
    
    # Suggestion based on speed
    if avg_time > 180:  # More than 3 minutes per quiz
        suggestions.append({
            "title": "Improve quiz speed",
            "detail": "Take timed quizzes to improve pacing to under 150 seconds."
        })
    
    # Get strong areas for motivation
    strong_progress = db.query(models.Progress).filter(
        models.Progress.student_id == student_id,
        models.Progress.accuracy >= 80
    ).order_by(desc(models.Progress.accuracy)).first()
    
    if strong_progress and len(suggestions) < 3:
        chapter = db.query(models.Chapter).filter_by(
            chapter_id=strong_progress.chapter_id
        ).first()
        chapter_name = chapter.chapter_name if chapter else f"Chapter {strong_progress.chapter_id}"
        
        suggestions.append({
            "title": f"Maintain excellence in {chapter_name}",
            "detail": f"Outstanding {float(strong_progress.accuracy):.1f}% accuracy! Keep revising to retain mastery."
        })
    
    # General suggestion if no specific areas
    if not suggestions:
        suggestions.append({
            "title": "Keep up the great work!",
            "detail": "Continue your consistent study habits and regular practice."
        })
    
    return suggestions[:3]  # Return max 3 suggestions

@app.post("/generate_mock_test")
async def generate_mock_test(request: Request, db: Session = Depends(get_db)):
    """
    Generate a comprehensive mock test covering multiple chapters.
    Used for Class 11 and Class 12 full mock tests (20 questions each).
    """
    body = await request.json()
    
    try:
        chapter_ids = body.get("chapter_ids", [])
        num_questions = body.get("num_questions", 20)
        class_type = body.get("class_type", "class11")
        
        if not chapter_ids:
            raise HTTPException(status_code=400, detail="chapter_ids is required")
        
        # Fetch NCERT content for ALL selected chapters
        all_ncert_rows = []
        for chapter_id in chapter_ids:
            q = db.query(models.Ncert).filter(models.Ncert.chapter_id == chapter_id)
            rows = q.limit(10).all()  # ~10 rows per chapter for balanced coverage
            all_ncert_rows.extend(rows)
        
        if not all_ncert_rows:
            return {"quiz": [], "error": "Not enough NCERT content found for mock test generation."}
        
        # Build context from all chapters
        context_parts = []
        for row in all_ncert_rows:
            if row.ncert_text:
                # Add chapter identifier to help AI distribute questions
                chapter = db.query(models.Chapter).filter_by(chapter_id=row.chapter_id).first()
                chapter_name = chapter.chapter_name if chapter else f"Chapter {row.chapter_id}"
                context_parts.append(f"[{chapter_name}]\n{row.ncert_text}")
        
        context = "\n\n".join(context_parts)
        if len(context) > 20000:
            context = context[:20000]
        
        if not context or len(context) < 100:
            return {"quiz": [], "error": "Not enough NCERT content found for quiz generation."}
        
        # Prepare Groq API request
        groq_url = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
        groq_key = os.getenv("GROQ_API_KEY")
        
        if not groq_url or not groq_key:
            raise HTTPException(status_code=500, detail="Groq API not configured")
        
        # Get chapter names for better prompting
        chapter_names = []
        for chapter_id in chapter_ids:
            chapter = db.query(models.Chapter).filter_by(chapter_id=chapter_id).first()
            if chapter:
                chapter_names.append(chapter.chapter_name)
        
        chapters_list = ", ".join(chapter_names[:10]) + ("..." if len(chapter_names) > 10 else "")
        
        # System prompt for mock test generation (same style as existing quiz generation)
        system_prompt = f"""You are an expert NEET Biology question generator creating a MOCK TEST covering multiple chapters.

Create {num_questions} high-quality multiple-choice questions distributed across the following chapters:
{chapters_list}

CRITICAL DISTRIBUTION REQUIREMENTS:
- Generate questions EVENLY across ALL chapters provided
- Aim for approximately {num_questions // len(chapter_ids)} questions per chapter
- Do NOT focus on just 2-3 chapters - cover ALL chapters comprehensively
- Ensure diverse topic coverage within each chapter

CRITICAL: AVOID REPETITION
- Do NOT generate questions similar to previously generated questions
- Vary specific topics, concepts, and angles being tested
- If a concept was tested before, approach it from a completely different perspective
- Focus on different subsections and applications from each chapter

STRICT REQUIREMENTS:

1. CONTENT ALIGNMENT:
   - Every question MUST be derived directly from the provided NCERT chapter content
   - Do NOT use external knowledge or information beyond the given NCERT text
   - Questions should cover key concepts, definitions, processes, and examples mentioned in chapters
   - Use the [Chapter Name] markers in context to identify and distribute questions

2. NEET DIFFICULTY STANDARD:
   - Questions must match authentic NEET exam difficulty (moderate to hard)
   - Include a mix of: 40% factual recall, 35% application-based, 25% conceptual understanding
   - Avoid overly easy or trivial questions that test only surface-level memorization
   - Create questions that require careful reading and critical thinking

3. QUESTION STRUCTURE:
   - Each question must have EXACTLY 4 options labeled A, B, C, D
   - Options should be similar in length (within 2-3 words difference)
   - All options must be grammatically parallel and stylistically consistent
   - Avoid patterns like "all of the above" or "none of the above" unless absolutely necessary

4. OPTION QUALITY (CRITICAL):
   - Correct answer must be definitively correct based on NCERT content
   - All 3 distractors must be highly plausible and scientifically reasonable
   - Distractors should be based on:
     * Common student misconceptions
     * Related but incorrect concepts from the same chapter
     * Partial truths or incomplete statements
     * Similar-sounding terms or processes
   - Avoid obviously wrong answers (like joke options or absurd statements)
   - Make the student think carefully between 2-3 options

5. SCIENTIFIC RIGOR:
   - Use precise scientific terminology as given in NCERT
   - Maintain taxonomic accuracy (correct genus, species, family names)
   - Include proper units, values, and ranges where applicable
   - Use standard nomenclature and conventions

6. EXPLANATION REQUIREMENTS:
   - Start with NCERT reference: "According to NCERT [Chapter Name]..."
   - Quote exact relevant lines from NCERT that support the correct answer
   - Explain clearly WHY the correct answer is right
   - Explain WHY each distractor is incorrect with specific reasoning
   - Connect explanation back to the chapter's key concepts
   - Keep explanations comprehensive but concise (4-6 sentences)

7. QUESTION DIVERSITY:
   - Vary question types: definitions, functions, examples, comparisons, sequences, exceptions, processes
   - Cover different topics within each chapter evenly
   - Alternate question stems: "Which of the following...", "Identify the correct...", "What is the role of...", "During which process..."
   - Include statement-based questions (Statement I and II format) when appropriate
   - Test relationships between concepts, not just isolated facts

FORMAT YOUR RESPONSE AS VALID JSON ONLY:
{{
  "questions": [
    {{
      "question": "Complete question text here",
      "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
      "correct_answer": "A",
      "explanation": "According to NCERT [Chapter], '[exact quote from NCERT]'. This establishes that [explanation]. Option B is incorrect because [reason]. Option C is incorrect because [reason]. Option D is incorrect because [reason].",
      "chapter_name": "Chapter Name Here"
    }}
  ]
}}

NCERT CONTEXT (Multiple Chapters):
{context}

Generate exactly {num_questions} UNIQUE questions distributed across ALL chapters. Return ONLY valid JSON, no additional text before or after."""
        
        # Call Groq API
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 6000
        }
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(groq_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            # Extract AI response
            ai_response = None
            if result.get("choices") and isinstance(result["choices"], list) and result["choices"]:
                message = result["choices"][0].get("message")
                if message and isinstance(message, dict) and message.get("content"):
                    ai_response = message["content"]
            
            if not ai_response:
                raise HTTPException(status_code=500, detail="Invalid response from AI")
            
            # Parse JSON response
            # Try to extract JSON from response (in case there's extra text)
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise HTTPException(status_code=500, detail="AI did not return valid JSON")
            
            json_str = ai_response[json_start:json_end]
            quiz_data = json.loads(json_str)
            
            # Validate and format questions
            questions = quiz_data.get("questions", [])
            
            if not questions:
                raise HTTPException(status_code=500, detail="No questions generated")
            
            # Format for frontend
            formatted_quiz = []
            for q in questions[:num_questions]:  # Ensure we don't exceed requested number
                opts = q.get("options", [])[:4]
                # ensure exactly 4 options; pad if necessary (shouldn't be needed but defensive)
                while len(opts) < 4:
                    opts.append("")
                formatted_quiz.append({
                    "question": q.get("question", "").strip(),
                    "options": opts,
                    "correct_answer": q.get("correct_answer", "A"),
                    "explanation": q.get("explanation", ""),
                    "chapter_name": q.get("chapter_name", "Mixed")
                })
            
            return {
                "quiz": formatted_quiz, 
                "topic": f"{class_type.upper()} Mock Test",
                "total_questions": len(formatted_quiz)
            }
            
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except httpx.HTTPStatusError as e:
        print(f"Groq API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=500, detail="AI service error")
    except Exception as e:
        print(f"Mock test generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
