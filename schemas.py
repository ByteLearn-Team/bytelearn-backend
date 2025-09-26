from pydantic import BaseModel
from typing import Optional

# --- Student ---
class StudentCreate(BaseModel):
    name: str
    email: str
    password_hash: str
    class_id: Optional[int] = None  # <-- Make optional

class StudentOut(BaseModel):
    student_id: int
    name: str
    email: str
    class_id: Optional[int] = None  # <-- Make this Optional

    class Config:
        from_attributes = True

# --- Class ---
class ClassCreate(BaseModel):
    class_id: int
    class_name: str

class ClassOut(BaseModel):
    class_id: int
    class_name: str

    class Config:
        from_attributes = True

# --- Subject ---
class SubjectCreate(BaseModel):
    subject_id: int
    subject_name: str
    class_id: int

class SubjectOut(BaseModel):
    subject_id: int
    subject_name: str
    class_id: int

    class Config:
        from_attributes = True

# --- Chapter ---
class ChapterCreate(BaseModel):
    chapter_id: int
    chapter_name: str
    subject_id: int

class ChapterOut(BaseModel):
    chapter_id: int
    chapter_name: str
    subject_id: int

    class Config:
        from_attributes = True

# --- Summary ---
class SummaryCreate(BaseModel):
    summary_id: int
    summary_data: str
    chapter_id: int

class SummaryOut(BaseModel):
    summary_id: int
    summary_data: str
    chapter_id: int

    class Config:
        from_attributes = True

# --- Flashcard ---
class FlashcardCreate(BaseModel):
    flashcard_id: int
    flashcard_data: str
    chapter_id: int

class FlashcardOut(BaseModel):
    flashcard_id: int
    flashcard_data: str
    chapter_id: int

    class Config:
        from_attributes = True

# --- Image ---
class ImageCreate(BaseModel):
    image_id: int
    image_url: str
    image_topic: str
    summary_id: int

class ImageOut(BaseModel):
    image_id: int
    image_url: str
    image_topic: str
    summary_id: int

    class Config:
        from_attributes = True

# --- NCERT ---
class NcertCreate(BaseModel):
    ncert_id: int
    ncert_text: str
    text_name: str

class NcertOut(BaseModel):
    ncert_id: int
    ncert_text: str
    text_name: str

    class Config:
        from_attributes = True
