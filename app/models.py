from sqlalchemy import Column, Float, ForeignKey, Integer, String, Table, create_engine
from .database import Base
from sqlalchemy.orm import relationship

student_subjects = Table(
    'student_subjects',
    Base.metadata,
    Column('student_id', Integer, ForeignKey('students.id'),primary_key=True),
    Column('subject_id', Integer, ForeignKey('subjects.id'),primary_key=True)
)

class StudentDB(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True)
    score = Column(Float, nullable=False)
    phones = relationship("PhoneDB", back_populates="student",cascade="all, delete-orphan")

    subjects = relationship("SubjectDB",
                secondary=student_subjects,
                back_populates="students"
                         )

    
class PhoneDB(Base):
    __tablename__ = "phones"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone_no = Column(String)
    student_id = Column(Integer, ForeignKey("students.id"))
    student = relationship("StudentDB", back_populates="phones")

class SubjectDB(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, index=True)
    students = relationship("StudentDB",
                secondary=student_subjects,
                back_populates="subjects")