from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

# Database
from Andromeda.api.database.init_db import init_db
from Andromeda.api.database.database import engine, get_session

# Routes
from Andromeda.api.routes import auth, api_keys


# Models
from Andromeda.models.user import User, UserKey

# Schemas
from Andromeda.schemas.user import UserCreate, UserPublic
from Andromeda.schemas.jwt import JWTPayload

# Auth
from Andromeda.auth.dependancies import get_current_user, require_scope


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


app.include_router(auth.router)
app.include_router(api_keys.router)



# --------------- Internal ---------------
# This section contains internal, Galacti specific functions.
# They are not publicly accessible under normal operating conditions.

@app.post("/users", response_model=UserPublic)
async def create_user(payload: UserCreate):
    async with AsyncSession(engine) as session:
        user = User.model_validate(payload)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@app.get("/users",response_model=list[UserPublic])
async def read_users(user: JWTPayload = Depends(require_scope("user:view"))):
    if not user:
        raise HTTPException(status_code=403, detail="Access denied, you do not have the right permissions to use this path")

    async with AsyncSession(engine) as session:
        result = await session.exec(select(User))
        users = result.all()
        return users



# --------------- External ---------------
# This section contains external and public functions.
# They are intended to be publicly accessible at all times.

@app.get("/")
async def root_get():
    return {"info":"Andromeda API is online.", "version":"v0.0.1"}