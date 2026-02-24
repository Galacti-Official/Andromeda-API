from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

# Database
from Andromeda.api.database.database import get_session

# Security
from Andromeda.auth.hashing import hash_password

# Models
from Andromeda.models.user import User

# Schemas 
from Andromeda.schemas.user import UserCreate


async def create_user(request: UserCreate) -> User:
    async with get_session() as session:
        user = User(
            name = request.name,
            email = request.email,
            password_hash = hash_password(request.password),
            last_login = None
        )

        session.add(user)

        try:
            await session.commit()
            await session.refresh(user)
            return user
        except Exception as e:
            print(f"Error: {e}")
            raise


async def reset_password():
    pass