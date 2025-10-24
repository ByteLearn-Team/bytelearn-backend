# Imports for data validation and structure
from pydantic import BaseModel      # Base class for building Python classes that describe data formats ("schemas")
from typing import Optional         # Lets us say something (like a field) is optional (doesn’t have to be filled)

# ==================================
# STUDENT SCHEMA
# ==================================

class StudentCreate(BaseModel):
    # This is the shape of data we need to create/add a new student (from API or code)
    name: str                         # Name of the student (text)
    email: str                        # Email of the student (text)
    password_hash: str                # Password as a hashed/scrambled string
    class_id: Optional[int] = None    # Class is optional—might be left out
    profile_picture: Optional[str] = None  # optional base64/data-url

class StudentOut(BaseModel):
    # This is the shape of data we send back when showing student info
    student_id: int                   # The unique ID assigned to the student in the database
    name: str                         # Name of the student
    email: str                        # Email of the student
    class_id: Optional[int] = None    # Class ID (might be missing)
    profile_picture: Optional[str] = None
    class Config:
        from_attributes = True        # Tells Pydantic to fill this from ORM models automatically

# ==================================
# CLASS SCHEMA
# ==================================

class ClassCreate(BaseModel):
    # Shape of data needed to create a new class
    class_id: int                     # Class's unique ID (sometimes set by user, sometimes auto)
    class_name: str                   # Name of the class

class ClassOut(BaseModel):
    # Shape of data sent back when showing class info
    class_id: int                     # Class's unique ID
    class_name: str                   # Name of the class
    class Config:
        from_attributes = True        # Fill fields from ORM models if possible

# ==================================
# SUBJECT SCHEMA
# ==================================

class SubjectCreate(BaseModel):
    subject_id: int                   # Unique ID for the subject
    subject_name: str                 # Name of the subject
    class_id: int                     # Class this subject belongs to

class SubjectOut(BaseModel):
    subject_id: int                   # Unique ID for the subject
    subject_name: str                 # Name of the subject
    class_id: int                     # Class this subject belongs to
    class Config:
        from_attributes = True        # Fill from ORM

# ==================================
# CHAPTER SCHEMA
# ==================================

class ChapterCreate(BaseModel):
    chapter_id: int                   # Unique ID for the chapter
    chapter_name: str                 # Name/title of the chapter
    subject_id: int                   # Subject this chapter belongs to

class ChapterOut(BaseModel):
    chapter_id: int                   # Unique ID for the chapter
    chapter_name: str                 # Name/title of the chapter
    subject_id: int                   # Subject this chapter belongs to
    class Config:
        from_attributes = True        # Fill from ORM

# ==================================
# SUMMARY SCHEMA
# ==================================

class SummaryCreate(BaseModel):
    summary_id: int                   # Unique ID for the summary
    summary_data: str                 # The main summary text
    chapter_id: int                   # Which chapter this summary belongs to

class SummaryOut(BaseModel):
    summary_id: int                   # Unique ID for the summary
    summary_data: str                 # The main summary text
    chapter_id: int                   # Which chapter this summary belongs to
    class Config:
        from_attributes = True        # Fill from ORM

# ==================================
# FLASHCARD SCHEMA
# ==================================

class FlashcardCreate(BaseModel):
    flashcard_id: int                 # Unique ID for the flashcard
    flashcard_data: str               # Text content of the flashcard
    chapter_id: int                   # Chapter this flashcard belongs to

class FlashcardOut(BaseModel):
    flashcard_id: int                 # Unique ID for the flashcard
    flashcard_data: str               # Text content of the flashcard
    chapter_id: int                   # Chapter this flashcard belongs to
    class Config:
        from_attributes = True        # Fill from ORM

# ==================================
# IMAGE SCHEMA
# ==================================

class ImageCreate(BaseModel):
    image_id: int                     # Unique ID for the image
    image_url: str                    # URL address of the image
    image_topic: str                  # Topic or description for the image
    summary_id: int                   # Which summary this image is attached to

class ImageOut(BaseModel):
    image_id: int                     # Unique ID for the image
    image_url: str                    # URL address of the image
    image_topic: str                  # Topic or description for the image
    summary_id: int                   # Which summary this image is attached to
    class Config:
        from_attributes = True        # Fill from ORM

# ==================================
# NCERT SCHEMA
# ==================================

class NcertCreate(BaseModel):
    ncert_id: int                     # Unique ID for the NCERT text chunk
    ncert_text: str                   # Actual NCERT textbook content
    text_name: str                    # Name of the part/chapter

class NcertOut(BaseModel):
    ncert_id: int                     # Unique ID for the NCERT text chunk
    ncert_text: str                   # Actual NCERT textbook content
    text_name: str                    # Name of the part/chapter
    class Config:
        from_attributes = True        # Fill from ORM

