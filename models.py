from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    ForeignKey, Numeric, Boolean
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


# --------------------
# Student & Class
# --------------------
class Student(Base):
    __tablename__ = "students"

    student_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(35), nullable=False)
    email = Column(String(40), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    classes = relationship("Class", back_populates="student")
    doubts = relationship("Doubt", back_populates="student")
    quizzes = relationship("Quiz", back_populates="student")
    progress = relationship("Progress", back_populates="student")


class Class(Base):
    __tablename__ = "classes"

    class_id = Column(Integer, primary_key=True, autoincrement=True)
    class_name = Column(String(35), nullable=False)
    student_id = Column(Integer, ForeignKey("students.student_id"))

    student = relationship("Student", back_populates="classes")
    subjects = relationship("Subject", back_populates="class_")


# --------------------
# Subject & Chapter
# --------------------
class Subject(Base):
    __tablename__ = "subjects"

    subject_id = Column(Integer, primary_key=True, autoincrement=True)
    subject_name = Column(String(35), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.class_id"))

    class_ = relationship("Class", back_populates="subjects")
    chapters = relationship("Chapter", back_populates="subject")


class Chapter(Base):
    __tablename__ = "chapters"

    chapter_id = Column(Integer, primary_key=True, autoincrement=True)
    chapter_name = Column(String(80), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.subject_id"))

    subject = relationship("Subject", back_populates="chapters")
    summaries = relationship("Summary", back_populates="chapter")
    flashcards = relationship("Flashcard", back_populates="chapter")
    doubts = relationship("Doubt", back_populates="chapter")
    quizzes = relationship("Quiz", back_populates="chapter")
    progress = relationship("Progress", back_populates="chapter")


# --------------------
# Summaries & Flashcards
# --------------------
class Summary(Base):
    __tablename__ = "summaries"

    summary_id = Column(Integer, primary_key=True, autoincrement=True)
    summary_data = Column(Text, nullable=False)  # LONGTEXT in MySQL
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))

    chapter = relationship("Chapter", back_populates="summaries")
    images = relationship("Image", back_populates="summary")


class Flashcard(Base):
    __tablename__ = "flashcards"

    flashcard_id = Column(Integer, primary_key=True, autoincrement=True)
    flashcard_data = Column(Text, nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))

    chapter = relationship("Chapter", back_populates="flashcards")


# --------------------
# Images
# --------------------
class Image(Base):
    __tablename__ = "images"

    image_id = Column(Integer, primary_key=True, autoincrement=True)
    image_url = Column(String(255), nullable=False)
    image_topic = Column(String(255), nullable=False)

    summary_id = Column(Integer, ForeignKey("summaries.summary_id"))
    question_id = Column(Integer, ForeignKey("quiz_items.question_id"))

    summary = relationship("Summary", back_populates="images")
    question = relationship("QuizItem", back_populates="images")


# --------------------
# Doubts & Responses
# --------------------
class Doubt(Base):
    __tablename__ = "doubts"

    doubt_id = Column(Integer, primary_key=True, autoincrement=True)
    doubt_question = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    student_id = Column(Integer, ForeignKey("students.student_id"))
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))

    student = relationship("Student", back_populates="doubts")
    chapter = relationship("Chapter", back_populates="doubts")
    responses = relationship("Response", back_populates="doubt")
    progress = relationship("Progress", back_populates="doubt")


class Response(Base):
    __tablename__ = "responses"

    response_id = Column(Integer, primary_key=True, autoincrement=True)
    doubt_response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    doubt_id = Column(Integer, ForeignKey("doubts.doubt_id"))

    doubt = relationship("Doubt", back_populates="responses")


# --------------------
# NCERT
# --------------------
class Ncert(Base):
    __tablename__ = "ncert"

    ncert_id = Column(Integer, primary_key=True, autoincrement=True)
    ncert_text = Column(Text, nullable=False)  # LONGTEXT in MySQL


# --------------------
# Quizzes, Questions, Options, Answers
# --------------------
class Quiz(Base):
    __tablename__ = "quizzes"

    quiz_id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    result_date = Column(DateTime, nullable=False)
    attempt_number = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    score = Column(Numeric(5, 2), nullable=False)

    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))
    student_id = Column(Integer, ForeignKey("students.student_id"))

    chapter = relationship("Chapter", back_populates="quizzes")
    student = relationship("Student", back_populates="quizzes")
    quiz_items = relationship("QuizItem", back_populates="quiz")
    progress = relationship("Progress", back_populates="quiz")


class QuizItem(Base):
    __tablename__ = "quiz_items"

    question_id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer_explain = Column(Text, nullable=False)

    quiz_id = Column(Integer, ForeignKey("quizzes.quiz_id"))
    quiz = relationship("Quiz", back_populates="quiz_items")

    options = relationship("Option", back_populates="question")
    answers = relationship("Answer", back_populates="question")
    images = relationship("Image", back_populates="question")


class Option(Base):
    __tablename__ = "options"

    option_id = Column(Integer, primary_key=True, autoincrement=True)
    opt = Column(String(35), nullable=False)
    correct = Column(String(11), nullable=False)

    question_id = Column(Integer, ForeignKey("quiz_items.question_id"))
    question = relationship("QuizItem", back_populates="options")


class Answer(Base):
    __tablename__ = "answers"

    answer_id = Column(Integer, primary_key=True, autoincrement=True)
    is_correct = Column(Boolean, nullable=False)

    option_id = Column(Integer, ForeignKey("options.option_id"))
    question_id = Column(Integer, ForeignKey("quiz_items.question_id"))

    question = relationship("QuizItem", back_populates="answers")


# --------------------
# Progress
# --------------------
class Progress(Base):
    __tablename__ = "progress"

    progress_id = Column(Integer, primary_key=True, autoincrement=True)
    avg_time = Column(Numeric(5, 2), nullable=False)
    accuracy = Column(Numeric(5, 2), nullable=False)
    weak_area = Column(Text, nullable=False)
    strong_area = Column(Text, nullable=False)

    student_id = Column(Integer, ForeignKey("students.student_id"))
    quiz_id = Column(Integer, ForeignKey("quizzes.quiz_id"))
    doubt_id = Column(Integer, ForeignKey("doubts.doubt_id"))
    chapter_id = Column(Integer, ForeignKey("chapters.chapter_id"))

    student = relationship("Student", back_populates="progress")
    quiz = relationship("Quiz", back_populates="progress")
    doubt = relationship("Doubt", back_populates="progress")
    chapter = relationship("Chapter", back_populates="progress")
