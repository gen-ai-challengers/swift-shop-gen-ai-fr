import jwt
import os
import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Response, UploadFile

from sqlalchemy.orm import Session

from ..domain.user import service, schemas

from ..dependencies import set_cookie

SECRET_KEY = os.getenv("JWT_SECRET_KEY" , "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")

COOKIE_HTTP_ONLY = os.getenv("COOKIE_HTTP_ONLY", 1) == 1
COOKIE_SECURE = os.getenv("COOKIE_SECURE", 1) == 1
ALGORITHM = "HS256"


router = APIRouter(tags=["auth"])

@router.post("/login/", response_model=dict)
def login(user: schemas.UserLogin, request: Request,response: Response):

    db: Session = request.state.db
    db_user = service.get_user_by_email(db, email=user.email)
    
    if not (db_user and bcrypt.checkpw(user.password.encode("utf-8"), db_user.hashed_password.encode("utf-8"))):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    set_cookie(response, db_user)

    return {"message": f"JWT token generated successfully for user {db_user.id}", "user": schemas.User(**db_user.__dict__).model_dump()}

@router.post("/register/", response_model=dict)
def register(user: schemas.UserCreate, request: Request,response: Response):

    db: Session = request.state.db
    db_user = service.create_user(db, user=user)

    set_cookie(response, db_user)
    return {"message": f"JWT token generated successfully for user {db_user.id}", "user": schemas.User(**db_user.__dict__).model_dump()}

@router.post("/recognize", response_model=dict)
async def recognize(request: Request,response: Response, file: UploadFile):
    logging.warning(f"Recognizing user by face")
    logging.warning(f"File Size: {file.size}")
    logging.warning(f"File Name: {file.filename}")
    db: Session = request.state.db
    db_user = await service.get_user_by_face(db, file)
    logging.warning(f"User found: {db_user}")
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    set_cookie(response, db_user)
    logging.warning(f"User found: {db_user.email}")
    return {"message": f"JWT token generated successfully for user {db_user.id}", "user": schemas.User(**db_user.__dict__).model_dump()}