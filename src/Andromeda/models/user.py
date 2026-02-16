from sqlmodel import SQLModel, Field, Relationship

from uuid import UUID, uuid4
from datetime import datetime, timezone


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    keys: list["UserKeys"] = Relationship(back_populates="user")


class UserKeys(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    secret_hash: str
    is_active: bool = Field(default=True)

    
    
