import logging
from fastapi import Depends, FastAPI, Request, Response

from fastapi.middleware.cors import CORSMiddleware

from starlette.exceptions import HTTPException

from .src.routers.api import router as router_api

from .src.database import engine, SessionLocal, Base

from .src.config import API_PREFIX, ALLOWED_HOSTS

from .src.routers.handlers.http_error import http_error_handler

from contextlib import asynccontextmanager

from sqlalchemy import text
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
        logging.info("Creating extension vector")
        session = SessionLocal()
        logging.info("Session created")
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logging.info("Extension vector created")
        session.commit()
        session.close()
    except Exception as e:
        logging.error(f"Error creating extension: {e}")
    # Generate database tables
    Base.metadata.create_all(bind=engine)
    # Mapping api routes
    application.include_router(router_api, prefix=API_PREFIX)

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
    response = Response("Internal server error", status_code=500)
    try:
        logging.info("Creating session")
        request.state.db = SessionLocal()
        logging.info("Session created")
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response
