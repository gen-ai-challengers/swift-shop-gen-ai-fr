from fastapi import APIRouter

from ..config import ROUTE_PREFIX_V1

from . import  users, auth, webrtc_fr

router = APIRouter()

def include_api_routes():
    ''' Include to router all api rest routes with version prefix '''
    router.include_router(auth.router)
    router.include_router(webrtc_fr.router)
    router.include_router(users.router, prefix=ROUTE_PREFIX_V1)

include_api_routes()