from fastapi import FastAPI , HTTPException , status
from typing import List
from pydantic import BaseModel

app = FastAPI()

class Student(BaseModel):
    id: int
    name: str
    score: int

students: List[Student] = [
    Student(id=1, name="John Doe", score=20),
    Student(id=2, name="John chawrai", score=30),
    Student(id=3, name="JJTopform", score=40),
]

# get all
@app.get("/students", response_model=List[Student])
async def get_students():
    return students

@app.get("/students/{student_id}", response_model=Student)
async def get_student_by_id(student_id: int):
    for student in students:
        if student.id == student_id:
            return student

    raise HTTPException(status_code=404, detail="Student not found")

@app.post("/students", 
          response_model=Student,
          status_code=status.HTTP_200_OK)
async def create_student(student: Student):
    students.append(student)
    return student

@app.delete("/students/{student_id}", status_code=status.HTTP_200_OK)
async def delete_student_by_id(student_id : int) :
    for index, student in enumerate(students):
        if student.id == student_id :
           deleted_student = students.pop(index)
           return {"message" : "Delete student successfully",
                   "data": deleted_student}

    raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {student_id} not found"
        )









