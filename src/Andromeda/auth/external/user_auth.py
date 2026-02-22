from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import jwt

from Andromeda.auth.hashing import verify_secret
from Andromeda.api.database.database import engine
from Andromeda.models.user import UserKey
from Andromeda.schemas.jwt import JWTPayload
from Andromeda.config import settings


async def auth_user_key(key: str) -> str:
    key_components = key.split("_")

    if len(key_components) != 4:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if key_components[0] != "sk":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if key_components[1] != "live":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    async with AsyncSession(engine) as session:
        result = await session.exec(select(UserKey).where(UserKey.kid == key_components[2]))
        user_key = result.first()

        if user_key is None:
            raise HTTPException(status_code=401, detail="Invalid API key")

        if not user_key.is_active:
            raise HTTPException(status_code=401, detail="Invalid API key")

        if not verify_secret(user_key.secret_hash, key_components[3]):
            raise HTTPException(status_code=401, detail=f"Invalid API key")
        
        encoded_jwt = jwt.encode(
            {
                "sub": f"client:{user_key.kid}",
                "scopes": user_key.scopes,
                "iss": settings.user_jwt_iss,
                "aud": settings.user_jwt_aud,
                "iat": datetime.now(timezone.utc),
                "nbf": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1)             
            },
            settings.jwt_private_key,
            algorithm="RS256"
        )

    return encoded_jwt


async def verify_jwt(token: str) -> JWTPayload:
    try:
        decoded = jwt.decode(
            token,
            settings.jwt_public_key,
            issuer=settings.user_jwt_iss,
            audience=settings.user_jwt_aud,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_nbf": True,
                "require": ["sub", "exp", "iat", "nbf", "iss", "aud", "scopes"]
            },
            algorithms=["RS256"]
        )

        return JWTPayload(**decoded)
    
    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    
    except jwt.exceptions.InvalidAudienceError:
        raise HTTPException(401, "Invalid audience")
    
    except jwt.exceptions.InvalidIssuerError:
        raise HTTPException(401, "Invalid issuer")
    
    except jwt.exceptions.PyJWTError:
        raise HTTPException(401, "Invalid token")
