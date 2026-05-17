import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import jobs

app = FastAPI(title="Malrocut AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])

@app.on_event("startup")
def startup_event():
    os.makedirs("backend/storage/jobs", exist_ok=True)
