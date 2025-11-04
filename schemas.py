from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# Each model corresponds to a MongoDB collection named by the lowercase class name
# Example: class User -> collection "user"

class User(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: EmailStr
    password_hash: str = Field(..., description="Hashed password with salt")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Course(BaseModel):
    slug: str = Field(..., min_length=2)
    title: str
    duration: str
    description: str
    projects: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Progress(BaseModel):
    user_id: str
    module: str
    done: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Note(BaseModel):
    user_id: str
    content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Reminder(BaseModel):
    user_id: str
    text: str
    time: str  # HH:MM
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
