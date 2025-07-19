from fastapi import APIRouter
from ..utils import Utils

health_check_router = APIRouter()

@health_check_router.get("/")
def healthcheck():
    Utils.debug_print("Healthcheck endpoint called")
    return {"status": "ok"}
