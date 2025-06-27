from fastapi import FastAPI
from src.bitbucket_service.routes.pr import pr_router
from src.bitbucket_service.utils.Utils import Utils

app = FastAPI()

Utils.debug_print("FastAPI app is starting up")

app.include_router(pr_router)

@app.get("/")
def healthcheck():
    Utils.debug_print("Healthcheck endpoint called")
    return {"status": "ok"} 