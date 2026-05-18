import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import jobs

app = FastAPI(title="Malrocut AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])

@app.on_event("startup")
def startup_event():
    # __file__ 기준 상위 2단계(backend/) 아래 storage/jobs 생성
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    os.makedirs(os.path.join(base, "storage", "jobs"), exist_ok=True)
