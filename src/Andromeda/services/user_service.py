from fastapi import FastAPI, HTTPException, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from uuid import UUID

# Database
from Andromeda.api.database.init_db import init_db
from Andromeda.api.database.database import engine, get_session

from Andromeda.models.user import User

# Schemas 
from Andromeda.schemas.user import UserCreate


async def create_user(user: UserCreate):
    async with get_session() as session:
        result = await session.exec(select(User))
        users = result.all()
    
    if user not in users:
        raise HTTPException(status_code=409, detail="User already exists")

    
async def authorize_user():
    pass