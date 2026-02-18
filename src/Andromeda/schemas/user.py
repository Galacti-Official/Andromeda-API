from sqlmodel import SQLModel
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from Andromeda.models.user import User, UserKey


class UserCreate(SQLModel):
    pass


class UserPublic(SQLModel):
    id: UUID
    created_at: datetime