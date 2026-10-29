from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Student(BaseModel):
    id: int
    name: str
    score: int

DEFAULT_STUDENTS: List[Student] = [
    Student(id=1, name="JJ", score=70),
    Student(id=2, name="John chawrai", score=45),
    Student(id=3, name="Jack russel", score=25)
]

students: List[Student] = list(DEFAULT_STUDENTS)

@app.get("/students", response_model=List[Student])
async def get_students(start: int | None = None, end: int | None = None):
    return students[start:end]

@app.get("/students/{student_id}", response_model=Student)
async def get_student(student_id: int):
    for student in students:
        if student.id == student_id:
            return student
    raise HTTPException(
        status_code=404,
        detail="Student not found"
        )

@app.post("/students", response_model=Student, status_code=status.HTTP_200_OK)
async def create_student(student: Student):
    for existing_student in students:
        if existing_student.id == student.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student with id {student.id} already exists"
            )
    students.append(student)
    return student



@app.delete("/students/{student_id}", status_code=status.HTTP_200_OK)
async def delete_student(student_id: int):
    for index, student in enumerate(students):
        if student.id == student_id:
            deleted_student = students.pop(index)
            return {"message": "Deleted student successfully", "data": deleted_student}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Student with id {student_id} not found"
        )

@app.put("/students/{student_id}", status_code=status.HTTP_200_OK)
async def update_student_by_id(student_id: int, updated_student: Student):
    for index, student in enumerate(students):
        if student.id == student_id:
            students[index] = updated_student
            return {"message": "Updated student successfully", "data": updated_student}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Item with ID {student_id} not found"
        )