from sqlmodel import SQLModel
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pydantic import BaseModel

from Andromeda.models.user import User, UserKey


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserCreateResponse(BaseModel):
    success: bool
    message: str
    user: User


class UserPublic(SQLModel):
    id: UUID
    name: str
    email: str
    avatar: str
    last_login: datetime
    created_at: datetime


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserLoginResponse(BaseModel):
    success: bool
    message: str
    user: User