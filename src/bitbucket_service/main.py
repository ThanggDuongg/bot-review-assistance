from fastapi import FastAPI
from dotenv import load_dotenv, find_dotenv
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path

env_file = find_dotenv()
env_path = Path(env_file)
print(f"File .env exists: {env_path.exists()}")
print(f"Absolute path: {env_path.absolute()}")

result = load_dotenv(env_path, override=True)
print(f"Load result: {result}")


from .routes import pr_router, health_check_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_check_router)
app.include_router(pr_router)

if __name__ == "__main__":
    uvicorn.run("src.bitbucket_service.main:app", host="localhost", port=8001, reload=False)