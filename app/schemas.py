from pydantic import BaseModel

#smaller data first cuz the big one dont have  key for the small one yet aa kaw jai mai


class Phone(BaseModel):
    phone_no: str

class PhoneCreate(Phone):
    pass

class PhoneResponse(Phone):
    id: int
    class Config:
        from_attributes = True

# ==========================
#    Subject 
# =========================
class Subject(BaseModel):
    name: str

class SubjectCreate(Subject):
    pass

class SubjectResponse(Subject):
    id: int
    class Config:
        from_attributes = True

# ======= Student ======
class Student(BaseModel):
    # id: int | None = None
    name: str
    score: float

# in
class StudentCreate(Student):
    # pass
    phones: list[PhoneCreate]

# out
class StudentResponse(Student):
    id: int
    phones: list[PhoneResponse]
    subjects: list[SubjectResponse]

    class Config:
        from_attributes = True