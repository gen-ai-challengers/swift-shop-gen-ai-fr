import bcrypt
import face_recognition
import io
import os
import logging
import PIL.Image
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy.sql import select
from . import models, schemas
from fastapi import UploadFile,HTTPException

vector = np.vectorize(np.float_)
GPU_ENABLED = os.getenv("GPU_ENABLED", 0) == 1
THRESHOLD = os.getenv("THRESHOLD", 0.6)

def get_user(db: Session, user_id: int) -> models.User:
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> models.User:
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db_user = models.User(email=user.email, hashed_password=hashed_password, name = user.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

async def get_user_by_face(db: Session, file: UploadFile):
    logging.warning(f"Recognizing user by face")
    request_object_content = await file.read()
    logging.warning("Opening image")
    image = PIL.Image.open(io.BytesIO(request_object_content))
    logging.warning("Converting image to RGB")
    image = image.convert("RGB")
    image = np.array(image)
    logging.warning("Detecting face")
    face_locations = face_recognition.face_locations(image)
    if len(face_locations) != 1:
        raise HTTPException(status_code=400, detail="Image must contain exactly one face")
    logging.warning("Encoding face")
    face_encodings = face_recognition.face_encodings(image, face_locations)
    logging.warning("Comparing face with database")
    face_encodings = vector(face_encodings[0])
    user = db.scalars(select(models.Face).order_by(models.Face.embedding.l2_distance(face_encodings)).limit(1)).first()
    logging.warning(f"User: {user}")
    if user is None:
        raise HTTPException(status_code=404, detail="Face not recognized")
    logging.warning("Checking threshold")
    distance = face_recognition.face_distance([user.embedding], face_encodings)
    logging.warning(f"Distance: {distance}")
    logging.warning(f"Threshold: {THRESHOLD}")
    if distance > THRESHOLD:
        logging.warning("Face not matched with any registered user")
        raise HTTPException(status_code=404, detail="Face not matched with any registered user")
    logging.warning(f"Recognized user {user.user_id}")
    logging.warning(f"User: {user.user}")
    return user.user

async def add_user_face(db: Session, file: UploadFile, user_id: int):
    logging.warning(f"Adding face to user {user_id}")
    logging.warning("Reading file content")
    request_object_content = await file.read()
    logging.warning("Opening image")
    image = PIL.Image.open(io.BytesIO(request_object_content))
    image = image.convert("RGB")
    image = np.array(image)
    logging.warning("Detecting face")
    face_locations = face_recognition.face_locations(image, model= "cnn" if GPU_ENABLED else "hog")
    logging.warning(f"Face locations: {len(face_locations)}")
    if len(face_locations) != 1:
        raise ValueError("Image must contain exactly one face")
    logging.warning("Encoding face")
    face_encodings = face_recognition.face_encodings(image, face_locations,model= "large" if GPU_ENABLED else "small")
    logging.warning("Adding face to database")
    face_encodings = vector(face_encodings[0])
    db_face = models.Face(embedding=face_encodings, user_id=user_id)
    db.add(db_face)
    db.commit()
    db.refresh(db_face)
    logging.warning(f"Face added to user {user_id}")