import logging

import base64
from typing import List,Annotated

from fastapi import APIRouter, Request, HTTPException, UploadFile, Depends

from sqlalchemy.orm import Session


from ..domain.user import service, schemas
from ..dependencies import validate_access_token, validate_permissions


router = APIRouter(tags=["users"])

@router.get("/users/me/", response_model=schemas.User, dependencies=[Depends(validate_access_token)])
def get_current_user(request: Request):
    db: Session = request.state.db
    db_user = service.get_user(db, user_id=request.state.user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found !")
    return db_user

@router.post("/users/", response_model=schemas.User, dependencies=[Depends(validate_access_token),Depends(validate_permissions)])
def create_user(user: schemas.UserCreate, request: Request):
    db: Session = request.state.db
    db_user = service.get_user_by_phone(db, phone=user.phone)
    if db_user:
        raise HTTPException(status_code=400, detail="phone already registered")
    return service.create_user(db=db, user=user)

@router.get("/users/", response_model=List[schemas.User], dependencies=[Depends(validate_access_token),Depends(validate_permissions)])
def read_users(request: Request, skip: int = 0, limit: int = 100):
    db: Session = request.state.db
    users = service.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/users/{user_id}/", response_model=schemas.User, dependencies=[Depends(validate_access_token),Depends(validate_permissions)])
def read_user(user_id: int, request: Request):
    db: Session = request.state.db
    db_user = service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.post("/users/me/add-face/", response_model=dict, dependencies=[Depends(validate_access_token)])
async def add_face(face: schemas.FaceFile, request: Request):
    user_id = request.state.user_id
    logging.warning(user_id)
    logging.warning(f"converting base64 to image")
    try:
        data_split = face.file.split('base64,')
        encoded_data = data_split[1]
        file = base64.b64decode(encoded_data)
    except Exception as e:
        logging.error(f"Error splitting data")
        logging.error(e)
        raise HTTPException(status_code=400, detail="Invalid data")
    db: Session = request.state.db
    db_user = service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    logging.warning(f"User found: {db_user.phone}")
    await service.add_user_face(db=db, file=file, user_id=user_id)
    return {"message": "Face added successfully"}


