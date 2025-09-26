from sqlalchemy.orm import Session
from models import Student, Class, Subject, Chapter, Summary, Flashcard, Image ,Ncert

# --- Students ---
def get_students(db: Session):
    return db.query(Student).all()

def create_student(db: Session, student_data):
    student = Student(
        name=student_data.name,
        email=student_data.email,
        password_hash=student_data.password_hash,
        class_id=student_data.class_id  # <-- ADD THIS
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student

# --- Classes ---
def get_classes(db: Session):
    return db.query(Class).all()

def create_class(db: Session, class_data):
    class_ = Class(
        class_id=class_data.class_id,
        class_name=class_data.class_name,
        student_id=class_data.student_id
    )
    db.add(class_)
    db.commit()
    db.refresh(class_)
    return class_

# --- Subjects ---
def get_subjects(db: Session):
    return db.query(Subject).all()

def create_subject(db: Session, subject_data):
    subject = Subject(
        subject_id=subject_data.subject_id,
        subject_name=subject_data.subject_name,
        class_id=subject_data.class_id
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject

# --- Chapters ---
def get_chapters(db: Session):
    return db.query(Chapter).all()

def create_chapter(db: Session, chapter_data):
    chapter = Chapter(
        chapter_id=chapter_data.chapter_id,
        chapter_name=chapter_data.chapter_name,
        subject_id=chapter_data.subject_id
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter

# --- Summaries ---
def get_summaries(db: Session):
    return db.query(Summary).all()

def create_summary(db: Session, summary_data):
    summary = Summary(
        summary_id=summary_data.summary_id,
        summary_data=summary_data.summary_data,
        chapter_id=summary_data.chapter_id
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary

# --- Flashcards ---
def get_flashcards(db: Session):
    return db.query(Flashcard).all()

def create_flashcard(db: Session, flashcard_data):
    flashcard = Flashcard(
        flashcard_id=flashcard_data.flashcard_id,
        flashcard_data=flashcard_data.flashcard_data,
        chapter_id=flashcard_data.chapter_id
    )
    db.add(flashcard)
    db.commit()
    db.refresh(flashcard)
    return flashcard

# --- Images ---
def get_images(db: Session):
    return db.query(Image).all()

def create_image(db: Session, image_data):
    image = Image(
        image_id=image_data.image_id,
        image_url=image_data.image_url,
        image_topic=image_data.image_topic,
        summary_id=image_data.summary_id
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image    
from models import Ncert

# --- NCERT ---
def get_ncerts(db: Session):
    return db.query(Ncert).all()

def create_ncert(db: Session, ncert_data):
    ncert = Ncert(
        ncert_id=ncert_data.ncert_id,  # remove if auto-increment
        ncert_text=ncert_data.ncert_text,
        text_name=ncert_data.text_name
    )
    db.add(ncert)
    db.commit()
    db.refresh(ncert)
    return ncert