import os
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utilities
SALT_LEN = 16

def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(SALT_LEN)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _hash = stored.split("$")
    except ValueError:
        return False
    return hash_password(password, salt) == stored


# Schemas for requests
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProgressRequest(BaseModel):
    user_id: str
    module: str
    done: bool

class NoteRequest(BaseModel):
    user_id: str
    content: str

class ReminderRequest(BaseModel):
    user_id: str
    text: str
    time: str  # HH:MM


@app.get("/")
def read_root():
    return {"message": "Getteng Apps Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = getattr(db, "name", None) or "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Auth endpoints (simple token-less demo)
@app.post("/auth/signup")
def signup(req: SignupRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    users = db["user"]
    if users.find_one({"email": req.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    doc = {
        "name": req.name.strip(),
        "email": req.email.lower(),
        "password_hash": hash_password(req.password),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    res = users.insert_one(doc)
    return {"user_id": str(res.inserted_id), "name": doc["name"], "email": doc["email"]}


@app.post("/auth/login")
def login(req: LoginRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    users = db["user"]
    user = users.find_one({"email": req.email.lower()})
    if not user or not verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # For simplicity, return a pseudo token (not JWT)
    token = secrets.token_urlsafe(24)
    return {"token": token, "user": {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}}


# Courses (static for now)
COURSES = [
    {
        "slug": "pengantar-rpl",
        "title": "Pengantar Rekayasa Perangkat Lunak",
        "duration": "6 jam",
        "description": "Konsep dasar RPL, SDLC, requirement, dan kualitas perangkat lunak.",
        "projects": ["Dokumen Requirement Sederhana", "Studi Kasus SDLC"],
    },
    {
        "slug": "algoritma",
        "title": "Algoritma & Struktur Data",
        "duration": "10 jam",
        "description": "Pemrograman dasar, kompleksitas, array, stack, queue, tree, graph.",
        "projects": ["Mini Library System", "Visualizer Sorting"],
    },
    {
        "slug": "oop",
        "title": "Pemrograman Berorientasi Objek (OOP)",
        "duration": "8 jam",
        "description": "Class, object, inheritance, polymorphism, SOLID principles.",
        "projects": ["Aplikasi Rental Sederhana", "Design Pattern Dasar"],
    },
    {
        "slug": "web",
        "title": "Pengembangan Web",
        "duration": "12 jam",
        "description": "HTML, CSS, JS, REST API, autentikasi, dan deployment dasar.",
        "projects": ["Landing Page Responsif", "CRUD App"],
    },
    {
        "slug": "ai",
        "title": "AI & Machine Learning Dasar",
        "duration": "10 jam",
        "description": "Pembelajaran mesin, model dasar, evaluasi, dan etika AI.",
        "projects": ["Klasifikasi Dataset Sederhana", "ML Pipeline Dasar"],
    },
    {
        "slug": "database",
        "title": "Basis Data",
        "duration": "8 jam",
        "description": "Model data, ERD, SQL/NoSQL, normalisasi, indexing, dan transaksi.",
        "projects": ["Desain ERD Proyek", "Query Optimization"],
    },
]

@app.get("/courses")
def list_courses():
    return {"items": COURSES}


# Study progress
@app.get("/progress")
def get_progress(user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    items = list(db["progress"].find({"user_id": user_id}))
    for it in items:
        it["id"] = str(it.pop("_id"))
    return {"items": items}


@app.post("/progress")
def upsert_progress(req: ProgressRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    col = db["progress"]
    col.update_one(
        {"user_id": req.user_id, "module": req.module},
        {"$set": {"done": req.done, "updated_at": datetime.now(timezone.utc)}, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return {"status": "ok"}


# Notes
@app.get("/notes")
def get_notes(user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    items = list(db["note"].find({"user_id": user_id}).sort("created_at", -1))
    for it in items:
        it["id"] = str(it.pop("_id"))
    return {"items": items}


@app.post("/notes")
def add_note(req: NoteRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = {"user_id": req.user_id, "content": req.content, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
    res = db["note"].insert_one(doc)
    return {"id": str(res.inserted_id)}


# Reminders
@app.get("/reminders")
def get_reminders(user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    items = list(db["reminder"].find({"user_id": user_id}).sort("created_at", -1))
    for it in items:
        it["id"] = str(it.pop("_id"))
    return {"items": items}


@app.post("/reminders")
def add_reminder(req: ReminderRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = {"user_id": req.user_id, "text": req.text, "time": req.time, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
    res = db["reminder"].insert_one(doc)
    return {"id": str(res.inserted_id)}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
