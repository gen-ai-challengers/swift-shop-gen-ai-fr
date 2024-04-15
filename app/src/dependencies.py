import os
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Annotated
from fastapi import Cookie,Response, HTTPException, Request
from .domain.user import models, schemas

SECRET_KEY = os.getenv("JWT_SECRET_KEY" , "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")

COOKIE_HTTP_ONLY = os.getenv("COOKIE_HTTP_ONLY", 1) == 1
COOKIE_SECURE = os.getenv("COOKIE_SECURE", 1) == 1
ALGORITHM = "HS256"
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", 1)

def create_access_token(data: models.User, expires_delta: Optional[timedelta] = None):
    

    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    user_token = schemas.User(**data.__dict__).model_dump()
    user_token.update({"exp": expire})
    logging.warning(f"Data: {user_token}")
    encoded_jwt =  jwt.encode(user_token, SECRET_KEY, algorithm=ALGORITHM)
    logging.warning(f"Encoded JWT for user id: {user_token.get('id')}")
    return encoded_jwt

def validate_access_token(x_session_token: Annotated[str, Cookie()]=None,request: Request=None):
    try:
        payload = jwt.decode(x_session_token, SECRET_KEY, algorithms=[ALGORITHM])
        logging.warning(f"Payload: {payload}")
        request.state.user_id = payload.get("id")
        logging.warning(f"User ID: {request.state.user_id}")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
def validate_permissions(request: Request=None):
    logging.warning("Validating permissions")
    path = request.url.path
    path = path.replace("/api/v1", "")
    logging.warning(f"Path: {path}")
    logging.warning(f"User ID: {request.state.user_id}")
    if path == "/users/":
        if not request.state.user_id == ADMIN_USER_ID:
            raise HTTPException(status_code=403, detail="Access denied only Admin have access")
    elif path.startswith("/users/") and not path.startswith("/users/"+str(request.state.user_id)):
        raise HTTPException(status_code=403, detail="Access denied only same user have access")   
    
def set_cookie(response: Response,db_user: models.User):
    token = create_access_token(db_user)
    response.set_cookie(key="x_session_token", value=token, httponly=COOKIE_HTTP_ONLY, secure=COOKIE_SECURE)
    response.set_cookie(key="x_user_id", value=str(db_user.id))
    response.set_cookie(key="x_phone", value=db_user.phone)
    response.set_cookie(key="x_is_active", value=str(db_user.is_active))
    response.set_cookie(key="x_username", value=db_user.name)
def remove_cookie(response: Response):
    response.delete_cookie("x_session_token")
    response.delete_cookie("x_user_id")
    response.delete_cookie("x_phone")
    response.delete_cookie("x_is_active")
    response.delete_cookie("x_username")
