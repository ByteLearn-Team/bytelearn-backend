# Imports for building database tables using SQLAlchemy library (super popular for Python databases!)
from sqlalchemy import (
    Column,        # Lets us define a "column" in each table
    Integer,       # Used for whole numbers (like 1, 2, 100)
    String,        # Used for short text (like names, emails)
    Text,          # Used for longer text (like a paragraph)
    DateTime,      # Used for storing dates and times (like when something happened)
    ForeignKey,    # Used to connect this table to another table
    Numeric,       # For numbers that can have decimals (like scores: 9.5)
    Boolean        # For values that are either True or False
)
from sqlalchemy.orm import relationship  # Helps us define connections between tables (like "Student belongs to Class")
from database import Base                # Every table will be based on this "Base" class (required for SQLAlchemy)
from datetime import datetime            # Used to get or store dates and times

# =======================
# Class Table
# =======================

class Class(Base):  # We're making a database table called 'classes'
    __tablename__ = "classes"  # This is the actual name of the table inside the database

    class_id = Column(Integer, primary_key=True, autoincrement=True)  # Each class gets its own unique ID number
    class_name = Column(String(35), nullable=False)  # The class name (can't be empty!)

    students = relationship("Student", back_populates="class_")  # This links all students IN the class
    subjects = relationship("Subject", back_populates="class_")  # This links all subjects FOR the class

# =======================
# Student Table
# =======================

class Student(Base):  # This makes a database table called 'students'
    __tablename__ = "students"  # Table name in the DB

    student_id = Column(Integer, primary_key=True, autoincrement=True)  # Unique number for each student
    name = Column(String(35), nullable=False)  # Their name, must be filled
    email = Column(String(40), nullable=False, unique=True)  # Their email, must be filled & unique
    password_hash = Column(String(255), nullable=False)  # Their password, safely stored (not raw text!)
    class_id = Column(Integer, ForeignKey("classes.class_id"), nullable=True)  # Which class the student is in

    is_verified = Column(Integer, nullable=False, default=0)  # 1 if email is verified, 0 if not
    otp_hash = Column(String(64), nullable=True)  # Stores their OTP as a secure hash (for registration)
    otp_expires_at = Column(DateTime, nullable=True)  # When the OTP will expire
    otp_attempts = Column(Integer, nullable=False, default=0)  # Tracks how many OTP tries they made
    otp_last_sent_at = Column(DateTime, nullable=True)
    
    # NEW: store profile picture as base64 or data-URL (nullable)
    profile_picture = Column(Text, nullable=True)

    class_ = relationship("Class", back_populates="students")
    doubts = relationship("Doubt", back_populates="student")  # All questions ("doubts") asked by this student
    quizzes = relationship("Quiz", back_populates="student")  # All quizzes this student took
    progress = relationship("Progress", back_populates="student")  # Progress tracking for this student

# =======================
# Pending Registration Table
# =======================

class PendingRegistration(Base):  # Used for students who started registration, but haven't verified OTP yet
    __tablename__ = "pending_registrations"  # Table name

    id = Column(Integer, primary_key=True, autoincrement=True)  # Unique ID for pending signup
    name = Column(String(35), nullable=False)  # Name of user as entered
    email = Column(String(40), nullable=False, unique=True)  # Must be unique
    password_hash = Column(String(255), nullable=False)  # Password (hashed for safety)
    class_id = Column(Integer, nullable=True)  # What class did they select (can be empty)

    otp_hash = Column(String(64), nullable=True)  # Their OTP code (as secure hash)
    otp_expires_at = Column(DateTime, nullable=True)  # When does OTP expire
    otp_attempts = Column(Integer, nullable=False, default=0)  # How many times they tried the OTP so far
    otp_last_sent_at = Column(DateTime, nullable=True)  # When did we last send an OTP?

# =======================
# Subject Table
# =======================

class Subject(Base):
    __tablename__ = "subjects"

    subject_id = Column(Integer, primary_key=True, autoincrement=True)  # Unique ID for subject
    subject_name = Column(String(35), nullable=False)  # Name of subject ('Biology' etc)
    class_id = Column(Integer, ForeignKey("classes.class_id"))  # Which class this subject belongs to
    
    class_ = relationship("Class", back_populates="subjects")  # Let us find the class easily from this subject
    chapters = relationship("Chapter", back_populates="subject")  # All chapters inside this subject

# =======================
# Chapter Table
# =======================

class Chapter(Base):  # Represents a chapter inside a subject
    __tablename__ = "chapters"

    chapter_id = Column(Integer, primary_key=True, autoincrement=True)  # Unique ID for chapter
    chapter_name = Column(String(80), nullable=False)  # Name of chapter
    subject_id = Column(Integer, ForeignKey("subjects.subject_id"))  # Which subject this chapter belongs to
    
    subject = relationship("Subject", back_populates="chapters")  # Lets us easily find subject from chapter
    summaries = relationship("Summary", back_populates="chapter")  # All summaries in this chapter
    flashcards = relationship("Flashcard", back_populates="chapter")  # All flashcards in this chapter
    doubts = relationship("Doubt", back_populates="chapter")  # All doubts from this chapter
    quizzes = relationship("Quiz", back_populates="chapter")  # All quizzes from this chapter
    progress = relationship("Progress", back_populates="chapter")  # Progress tracking for this chapter

# =======================
# Summary Table
# =======================

class Summary(Base):  # Stores notes or summaries for a chapter
    __tablename__ = "summaries"

    summary_id = Column(Integer, primary_key=True, autoincrement=True)  # Unique ID for this summary
    summary_data = Column(Text, nullable=False)  # Actual summary content
    
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))  # Which chapter this summary belongs to
    chapter = relationship("Chapter", back_populates="summaries")
    images = relationship("Image", back_populates="summary")  # Any images attached to this summary

# =======================
# Flashcard Table
# =======================

class Flashcard(Base):  # Stores simple facts or Q&A for revision
    __tablename__ = "flashcards"

    flashcard_id = Column(Integer, primary_key=True, autoincrement=True)
    flashcard_data = Column(Text, nullable=False)  # The flashcard content (text)
    
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))  # Which chapter this flashcard belongs to
    chapter = relationship("Chapter", back_populates="flashcards")

# =======================
# Doubt Table (Student Questions)
# =======================

class Doubt(Base):  # Student's question about a chapter, for teacher/mod answers
    __tablename__ = "doubts"

    doubt_id = Column(Integer, primary_key=True, autoincrement=True)
    doubt_question = Column(Text, nullable=False)  # The question text itself
    created_at = Column(DateTime, default=datetime.utcnow)  # When did they ask?
    student_id = Column(Integer, ForeignKey("students.student_id"))  # Who asked the question
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))  # Which chapter is it about
    
    student = relationship("Student", back_populates="doubts")  # Easily get the student from doubt
    chapter = relationship("Chapter", back_populates="doubts")  # Easily get the chapter from doubt
    responses = relationship("Response", back_populates="doubt")  # All answers to this doubt
    progress = relationship("Progress", back_populates="doubt")

# =======================
# Response Table (Answers to Doubts)
# =======================

class Response(Base):  # Stores answers to student doubts
    __tablename__ = "responses"

    response_id = Column(Integer, primary_key=True, autoincrement=True)
    doubt_response = Column(Text, nullable=False)  # Actual answer text
    created_at = Column(DateTime, default=datetime.utcnow)
    doubt_id = Column(Integer, ForeignKey("doubts.doubt_id"))  # Which doubt is this answer for?
    
    doubt = relationship("Doubt", back_populates="responses")  # Easily get the doubt from response

# =======================
# NCERT Table (Official Text)
# =======================

class Ncert(Base):
    __tablename__ = "ncert"
    ncert_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ncert_text = Column(Text)
    text_name = Column(String(80))
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))

    chapter = relationship("Chapter")


# =======================
# Quiz Table
# =======================

class Quiz(Base):  # Tracks student's quiz attempts for each chapter
    __tablename__ = "quizzes"

    quiz_id = Column(Integer, primary_key=True, autoincrement=True)  # Unique quiz number
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)  # When the quiz was created
    result_date = Column(DateTime, nullable=False)  # When results were calculated
    attempt_number = Column(Integer, nullable=False)  # For repeat attempts
    started_at = Column(DateTime, nullable=False)  # Start time of the quiz
    ended_at = Column(DateTime, nullable=False)    # End time of the quiz
    score = Column(Numeric(5, 2), nullable=False)  # Score; supports decimals

    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))  # Which chapter this quiz is for?
    student_id = Column(Integer, ForeignKey("students.student_id"))  # Which student took this quiz?
    
    chapter = relationship("Chapter", back_populates="quizzes")
    student = relationship("Student", back_populates="quizzes")
    quiz_items = relationship("QuizItem", back_populates="quiz")  # All questions in this quiz
    progress = relationship("Progress", back_populates="quiz")

# =======================
# QuizItem Table (Questions)
# =======================

class QuizItem(Base):  # Each question in a quiz
    __tablename__ = "quiz_items"

    question_id = Column(Integer, primary_key=True, autoincrement=True)  # Unique question number
    question = Column(Text, nullable=False)  # The question text
    answer_explain = Column(Text, nullable=False)  # Explanation for the answer
    
    quiz_id = Column(Integer, ForeignKey("quizzes.quiz_id"))  # Which quiz does this question belong to?
    quiz = relationship("Quiz", back_populates="quiz_items")
    
    options = relationship("Option", back_populates="question")  # Possible answers/choices
    answers = relationship("Answer", back_populates="question")  # What student answered
    images = relationship("Image", back_populates="question")    # Any images for this question

# =======================
# Option Table (Choices for Quiz Questions)
# =======================

class Option(Base):  # Multiple choice options for quiz questions
    __tablename__ = "options"

    option_id = Column(Integer, primary_key=True, autoincrement=True)  # Unique option number
    opt = Column(String(35), nullable=False)  # The text shown for this option
    correct = Column(String(11), nullable=False)  # String that tells if this is the correct answer
    
    question_id = Column(Integer, ForeignKey("quiz_items.question_id"))  # Which question does this belong to?
    question = relationship("QuizItem", back_populates="options")

# =======================
# Answer Table (What the user answered)
# =======================

class Answer(Base):  # Tracks which answer a student picked, and if correct
    __tablename__ = "answers"

    answer_id = Column(Integer, primary_key=True, autoincrement=True)  # Unique answer number
    is_correct = Column(Boolean, nullable=False)  # True if right, False if wrong
    option_id = Column(Integer, ForeignKey("options.option_id"))  # Which option was picked
    question_id = Column(Integer, ForeignKey("quiz_items.question_id"))  # Which question was answered
    
    question = relationship("QuizItem", back_populates="answers")

# =======================
# Progress Table (Tracking student's performance)
# =======================

class Progress(Base):  # Helps track how a student is learning
    __tablename__ = "progress"

    progress_id = Column(Integer, primary_key=True, autoincrement=True)  # Unique progress number
    avg_time = Column(Numeric(5, 2), nullable=False)  # Average time per quiz item/chapter
    accuracy = Column(Numeric(5, 2), nullable=False)  # % correct answers
    weak_area = Column(Text, nullable=True)  # Student's weak topics/areas
    strong_area = Column(Text, nullable=True)  # Student's strong topics/areas
    
    student_id = Column(Integer, ForeignKey("students.student_id"))  # Who does this progress belong to?
    quiz_id = Column(Integer, ForeignKey("quizzes.quiz_id"))  # Progress on which quiz?
    doubt_id = Column(Integer, ForeignKey("doubts.doubt_id"))  # Progress on which doubt?
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))  # Progress on which chapter?
    
    student = relationship("Student", back_populates="progress")
    quiz = relationship("Quiz", back_populates="progress")
    doubt = relationship("Doubt", back_populates="progress")
    chapter = relationship("Chapter", back_populates="progress")
