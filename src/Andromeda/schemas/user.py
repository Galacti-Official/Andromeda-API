from sqlmodel import SQLModel
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel

from Andromeda.models.user import User, UserKey


class UserCreate(SQLModel):
    name: str
    email: str
    password_hash: str


class UserPublic(SQLModel):
    id: UUID
    created_at: datetime