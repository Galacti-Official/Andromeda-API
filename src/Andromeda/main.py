from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from Andromeda.api.database.init_db import init_db
from Andromeda.api.database.database import engine, get_session
from Andromeda.models.user import User, UserKey
from Andromeda.models.node import Node, NodeKey
from Andromeda.schemas.user import UserCreate, UserPublic


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)



# --------------- Internal ---------------
# This section contains internal, Galacti specific functions.
# They are not publicly accessible under normal operating conditions.




# --------------- External ---------------
# This section contains external and public functions.
# They are intended to be publicly accessible at all times.

@app.get("/")
async def root_get():
    return {"info":"Andromeda API is online.", "version":"v0.0.1"}