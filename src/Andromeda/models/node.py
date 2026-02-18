from sqlmodel import SQLModel, Field, Relationship
from typing import List
from uuid import UUID, uuid4
from datetime import datetime, timezone


class Node(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    keys: List["NodeKey"] = Relationship(back_populates="node")


class NodeKey(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    node_id: UUID = Field(foreign_key="node.id", index=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    secret_hash: str
    is_active: bool = Field(default=True)