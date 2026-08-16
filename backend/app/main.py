from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.database import engine
from app.routers import auth, users, food, logs

# Creates tables in MySQL if they don't already exist
# (your daily_logs and users tables already exist, so this is safe/no-op for them)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nutritional Tracking System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(food.router)
app.include_router(logs.router)

@app.get("/")
def read_root():
    return {"status": "Backend running successfully!"}