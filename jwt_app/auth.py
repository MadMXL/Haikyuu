
from datetime import datetime, timezone, timedelta
from pwdlib import PasswordHash
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
import jwt

from .db import get_db, UserDB
from .limiter import check_not_locked, record_failed_login, reset_failed_logins

router = APIRouter()

SECRET_KEY = "my-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
password_hash = PasswordHash.recommended()

# tokens that have been logged out, rejected even if not expired yet
blacklist = set()


class UserCreate(BaseModel):
    username: str
    password: str


@router.post("/register", status_code=201)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    db_user = UserDB(
        username=user.username,
        hashed_password=password_hash.hash(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"id": db_user.id, "username": db_user.username}


@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    check_not_locked(request)

    user = db.query(UserDB).filter(UserDB.username == form_data.username).first()

    if not user or not password_hash.verify(form_data.password, user.hashed_password):
        record_failed_login(request)
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    reset_failed_logins(request)

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    token = jwt.encode( {
        "sub": user.username,
        "exp": expire # Optional
    },
    SECRET_KEY, algorithm=ALGORITHM
    )

    return {
        "access_token" : token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    blacklist.add(token)
    return {"message": "Logged out successfully"}


def get_current_user(token: str = Depends(oauth2_scheme) ):
    if token in blacklist:
        raise HTTPException(status_code=401, detail="Token has been revoked")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return username
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
