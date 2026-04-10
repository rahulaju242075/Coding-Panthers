from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from database import engine, Base
import models
from routers import auth, patient, doctor

# Ensure uploads folder exists
os.makedirs("uploads/profiles", exist_ok=True)

# Create Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MediLink Health API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(patient.router)
app.include_router(doctor.router)

app.mount("/api/files", StaticFiles(directory="uploads"), name="uploads")

# Mount the frontend directories as static files
# Since backend/main.py is in stitch_medilink_health_ui/backend,
# the frontend root is '..' relative to this file.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# We will just mount the root as static, so accessing /landing_page/landing_page.html works
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
