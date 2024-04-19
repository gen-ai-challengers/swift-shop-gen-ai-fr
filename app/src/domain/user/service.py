import bcrypt
import os
import logging
from sqlalchemy.orm import Session
from sqlalchemy.sql import select
from . import models, schemas
from ...dependencies import check_matching, embed_single_face
from fastapi import  HTTPException




def get_user(db: Session, user_id: int) -> models.User:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_phone(db: Session, phone: str) -> models.User:
    return db.query(models.User).filter(models.User.phone == phone).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = bcrypt.hashpw(user.password.encode(
        'utf-8'), bcrypt.gensalt()).decode('utf-8')
    db_user = models.User(
        phone=user.phone, hashed_password=hashed_password, name=user.name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


async def get_user_by_face(db: Session, face: bytes):

    face_encodings = embed_single_face(face)
    user = db.scalars(select(models.Face).order_by(
        models.Face.embedding.l2_distance(face_encodings)).limit(1)).first()
    logging.warning(f"User: {user.user_id}")
    if user is None:
        raise HTTPException(status_code=404, detail="Face not recognized")
    logging.warning("Checking threshold")
    distance = check_matching([user.embedding], face_encodings)
    logging.warning(f"Distance: {distance}")
    logging.warning(f"Recognized user {user.user_id}")
    logging.warning(f"User: {user.user}")
    return user.user


async def add_user_face(db: Session, face: bytes, user_id: int):

    face_encodings = embed_single_face(face)
    db_face = models.Face(embedding=face_encodings, user_id=user_id)
    db.add(db_face)
    db.commit()
    db.refresh(db_face)
    logging.warning(f"Face added to user {user_id}")
