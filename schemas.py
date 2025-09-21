from pydantic import BaseModel

class StudentCreate(BaseModel):
    name: str
    email: str
    password_hash: str

class StudentOut(BaseModel):
    student_id: int
    name: str
    email: str

    class Config:
        from_attributes = True   # 👈 change from orm_mode to this
