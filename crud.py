from sqlalchemy.orm import Session
from models import Student

def get_students(db: Session):
    return db.query(Student).all()

def create_student(db: Session, student_data):
    student = Student(
        name=student_data.name,
        email=student_data.email,
        password_hash=student_data.password_hash
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student
