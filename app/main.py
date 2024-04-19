import logging
from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from fastapi.middleware.cors import CORSMiddleware

import psycopg2
from starlette.exceptions import HTTPException

from .src.routers.api import router as router_api

from .src.database import engine, SessionLocal, Base

from .src.config import API_PREFIX, ALLOWED_HOSTS

from .src.routers.handlers.http_error import http_error_handler

from contextlib import asynccontextmanager

from sqlalchemy import text

import tensorflow as tf
###
# Main application file
###


def get_application() -> FastAPI:
    ''' Configure, start and return the application '''

    # Start FastApi App
    application = FastAPI()

    origins = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://quiet-liberty-417104.web.app"
    ]


    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    try:
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            logging.warning(f"Num GPUs Available: {len(gpus)}")
            for gpu in gpus:
                logging.warning(f"GPU: {gpu}")
        else:
            logging.warning("No GPUs Available")            
            cpus = tf.config.list_physical_devices('CPU')
            if cpus:
                logging.warning(f"Num CPUs Available: {len(cpus)} ")
                for cpu in cpus:
                    logging.warning(f"CPU: {cpu}")    
                logging.warning("Creating extension vector")
            else:
                logging.warning("No CPUs Available")
        session = SessionLocal()
        logging.warning("Session created")
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logging.warning("Extension vector created")
        session.commit()
        session.close()
    except Exception as e:
        logging.error(f"Error creating extension: {e}")
    # Generate database tables
    Base.metadata.create_all(bind=engine)
    # Mapping api routes
    application.include_router(router_api, prefix=API_PREFIX)
    application.mount("/", StaticFiles(directory="public"), name="public")

    # Add exception handlers
    application.add_exception_handler(HTTPException, http_error_handler)

    return application


app = get_application()


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    '''
    The middleware we'll add (just a function) will create
    a new SQLAlchemy SessionLocal for each request, add it to
    the request and then close it once the request is finished.
    '''
    response = JSONResponse(content={"message": "Internal server error"}, status_code=500)
    try:
        logging.warning("Creating session")
        request.state.db = SessionLocal()
        logging.warning("Session created")
        response = await call_next(request)
    except Exception as e:
        logging.error(f"Exception: {type(e.__cause__)}")
        logging.error(f"Exception: {isinstance(e.__cause__, psycopg2.errors.UniqueViolation)}")
        if isinstance(e.__cause__, psycopg2.errors.UniqueViolation):
            logging.error(f">>>>> Duplicate key error: {e}")
            message = e.__cause__.diag.message_detail
            message = message.replace("Key", "Field")
            message = message.replace("=", " with value ")
            message = message.replace("(", "").replace(")", "")
            logging.error(f">>>>> Duplicate key error:{message}")
            response = JSONResponse(content={"message": message}, status_code=400)
        else:    
            logging.error(f"Unknown Exception: {e}")
    finally:
        request.state.db.close()
    return response
