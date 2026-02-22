import asyncio

from sqlmodel import SQLModel, text

from Andromeda.api.database.database import engine
import Andromeda.models


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)