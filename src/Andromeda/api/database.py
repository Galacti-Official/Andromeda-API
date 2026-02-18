import os
import asyncio
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio.session import async_sessionmaker


load_dotenv()

DATABASE_URL = str(os.getenv("DATABASE_URL"))

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)

async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def get_session():
    async with async_session() as session:
        yield session



