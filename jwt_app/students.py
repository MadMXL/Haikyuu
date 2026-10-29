from fastapi import APIRouter,  Depends 

from jwt_app.auth import get_current_user

router = APIRouter()

@router.get("/")
async def hello():
    return {"msg": "Hello"}

@router.get("/students")
async def get_students(username: str = Depends(get_current_user)):
    return {
        "message": "Authenticated user",
        "user": username,
        "students": [
            {"id": 1, "name": "John"},
            {"id": 2, "name": "jene"},
        ],
    }



