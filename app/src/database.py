from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os
###
# Database Configuration
###

HOST = os.getenv("DB_HOST", "localhost")
PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PWD = os.getenv("DB_PWD", "password")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PWD}@{HOST}:{PORT}/postgres"

engine = create_engine(
    os.getenv("DB_URL", SQLALCHEMY_DATABASE_URL)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



Base = declarative_base()
