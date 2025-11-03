# Import the Session class needed to talk to the database
from sqlalchemy.orm import Session
import schemas

# Import all the models (these represent our database tables)
from models import Student, Class, Subject, Chapter, Summary, Flashcard, Image, Ncert

# ============================================================
# STUDENT CRUD OPERATIONS (Create, Read)
# ============================================================

def get_students(db: Session):
    # Returns a list of all Student records in the database
    return db.query(Student).all()

def create_student(db: Session, student_data):
    # Adds a new student to the database using the info provided
    student = Student(
        name=student_data.name,                            # Student's name
        email=student_data.email,                          # Student's email
        password_hash=student_data.password_hash,          # Student's hashed password (for safety)
        class_id=student_data.class_id                     # Student's class (optional)
    )
    db.add(student)       # Add the new student to the database session
    db.commit()           # Save the changes to the database
    db.refresh(student)   # Get the latest info about the student (including assigned ID)
    return student        # Return the newly created student

# ============================================================
# CLASS CRUD OPERATIONS
# ============================================================

def get_classes(db: Session):
    # Returns a list of all Class records in the database
    return db.query(Class).all()

def create_class(db: Session, class_data):
    # Adds a new class to the database with the provided info
    class_ = Class(
        class_id=class_data.class_id,       # Unique ID (optional if set to auto-increment)
        class_name=class_data.class_name    # Name of the class
        # Note: You might want to remove student_id if not used in the model!
        # student_id=class_data.student_id
    )
    db.add(class_)         # Add the new class to the session
    db.commit()            # Save changes
    db.refresh(class_)     # Get latest info
    return class_          # Return the new class

# ============================================================
# SUBJECT CRUD OPERATIONS
# ============================================================

def get_subjects(db: Session):
    # Returns all Subject records in the database
    return db.query(Subject).all()

def create_subject(db: Session, subject_data):
    # Adds a new subject to the database
    subject = Subject(
        subject_id=subject_data.subject_id,   # Unique subject ID
        subject_name=subject_data.subject_name,# Subject name (e.g. Biology, Math)
        class_id=subject_data.class_id        # Which class is this for?
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject

# ============================================================
# CHAPTER CRUD OPERATIONS
# ============================================================

def get_chapters(db: Session):
    # Returns all chapters in the database
    return db.query(Chapter).all()

def create_chapter(db: Session, chapter_data):
    # Adds a new chapter to the database
    chapter = Chapter(
        chapter_id=chapter_data.chapter_id,     # Unique chapter ID
        chapter_name=chapter_data.chapter_name, # Chapter name (e.g. 'Nutrition')
        subject_id=chapter_data.subject_id      # Which subject it belongs to
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter

# ============================================================
# SUMMARY CRUD OPERATIONS
# ============================================================

def get_summaries(db: Session):
    # Returns all summaries in the database
    return db.query(Summary).all()

def create_summary(db: Session, summary_data):
    # Adds a new summary/notes to the database
    summary = Summary(
        summary_id=summary_data.summary_id,     # Unique summary ID
        summary_data=summary_data.summary_data, # Actual summary text/content
        chapter_id=summary_data.chapter_id      # Which chapter it's linked to
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary

# ============================================================
# FLASHCARD CRUD OPERATIONS
# ============================================================

def get_flashcards(db: Session):
    # Gets all flashcards from the database
    return db.query(Flashcard).all()

def create_flashcard(db: Session, flashcard_data):
    # Adds a new flashcard to the database
    flashcard = Flashcard(
        flashcard_id=flashcard_data.flashcard_id,   # Unique ID for the flashcard
        flashcard_data=flashcard_data.flashcard_data,# The content/text of the flashcard
        chapter_id=flashcard_data.chapter_id        # The chapter it's for
    )
    db.add(flashcard)
    db.commit()
    db.refresh(flashcard)
    return flashcard

# ============================================================
# NCERT CRUD OPERATIONS (for official textbook text)
# ============================================================

def get_ncerts(db: Session):
    # Returns all NCERT text entries from the database
    return db.query(Ncert).all()

def create_ncert(db: Session, ncert: schemas.NcertCreate):
    db_ncert = Ncert(
        ncert_text=ncert.ncert_text,
        text_name=ncert.text_name,
        chapter_id=ncert.chapter_id
    )
    db.add(db_ncert)
    db.commit()
    db.refresh(db_ncert)
    return db_ncert
