from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime
from typing import List, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone


class User(SQLModel, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    
    keys: List["UserKey"] = Relationship(back_populates="user")


class UserKey(SQLModel, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    
    secret_hash: str
    is_active: bool = Field(default=True)

    user: Optional["User"] = Relationship(back_populates="keys")