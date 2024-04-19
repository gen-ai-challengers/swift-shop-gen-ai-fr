
from pydantic import BaseModel
import numpy as np
import datetime


class FaceFile(BaseModel):
    file: str

class Face(BaseModel):
    id: int
    embedding: float = None
    owner_id: int

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    phone: str
    

class UserLogin(UserBase):
    password: str

class UserCreate(UserLogin):
    name: str


class User(UserBase):
    id: int
    is_active: bool
    name: str
    class Config:
        orm_mode = True