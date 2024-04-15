from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship,mapped_column
from pgvector.sqlalchemy import Vector
from ...database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    faces = relationship("Face", back_populates="user")


class Face(Base):
    __tablename__ = "faces"

    id = Column(Integer, primary_key=True, index=True)
    embedding = mapped_column(Vector(), index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="faces")
