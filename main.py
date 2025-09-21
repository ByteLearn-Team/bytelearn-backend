
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
import crud, schemas

app = FastAPI()

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





