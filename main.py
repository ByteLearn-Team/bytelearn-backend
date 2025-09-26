from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
import crud, schemas
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add this after app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only
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
def register(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing = db.query(crud.Student).filter_by(email=student.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_student(db, student)

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