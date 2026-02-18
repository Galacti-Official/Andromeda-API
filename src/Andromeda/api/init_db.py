from sqlmodel import SQLModel, text
from Andromeda.api.database import engine

import Andromeda.models
import asyncio

print(SQLModel.metadata.tables.keys())

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

