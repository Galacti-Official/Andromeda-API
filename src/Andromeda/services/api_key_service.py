import secrets
import base64
import shortuuid

from typing import Optional

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from Andromeda.api.database.database import engine
from Andromeda.auth.hashing import hash_secret

from Andromeda.models.user import User, UserKey

from Andromeda.schemas.key import CreateKeyRequest, CreatedKeyResponse
from Andromeda.schemas.jwt import JWTPayload


valid_user_types = ["user", "client", "node"]

valid_type_prefixes = ["sk", "nk", "wk", "mk", "fk"]
valid_env_types = ["live", "test"]



def gen_secret() -> str:
    raw = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def gen_kid() -> str:
    return shortuuid.uuid()


def format_key(prefix: str, type: str, kid: str, secret: str) -> str:
    if prefix not in valid_type_prefixes:
        raise ValueError(f"{prefix} is not a valid type prefix, use one of {valid_type_prefixes}")
    
    if type not in valid_env_types:
        raise ValueError(f"{type} is not a valid environment type, use one of {valid_env_types}")
    
    if len(kid) != 22:
        raise ValueError(f"kid must be 22 characters, got {len(kid)}")
    
    if len(secret) != 43:
        raise ValueError(f"secret must be 43 characters, got {len(secret)}")
    
    return f"{prefix}_{type}_{kid}_{secret}"



async def create_api_key(request: CreateKeyRequest, user: JWTPayload, session=AsyncSession(engine)) -> Optional[CreatedKeyResponse]:
    if request is None:
        raise HTTPException(status_code=400, detail="Invalid request")
    
    sub_components = user.sub.split(":")

    if len(sub_components) != 2 or sub_components[0] not in valid_user_types:
        raise HTTPException(status_code=403, detail="Invalid user type")
    
    if sub_components[0] == "client":
        client_kid = sub_components[1]

        result = await session.exec(select(User).join(UserKey).where(UserKey.kid == client_kid))
        client_user = result.first()

        if client_user is None:
            raise HTTPException(status_code=401, detail="Invalid user")

        key_name = request.name
        key_user_id = client_user.id
        key_scopes = request.scopes

        key_type_prefix = request.type
        key_env_type = request.env

        key_id = gen_kid()
        key_secret = gen_secret()

        key_secret_hash = hash_secret(key_secret)

        full_key = format_key(key_type_prefix, key_env_type, key_id, key_secret)

        key = UserKey(user_id=key_user_id, name = key_name, kid=key_id, secret_hash=key_secret_hash, scopes=key_scopes)
        session.add(key)
        await session.commit()
        await session.refresh(key)

        return CreatedKeyResponse(name=key_name, type=key_type_prefix, env=key_env_type, scopes=key_scopes, kid=key_id, secret=key_secret, key=full_key)
        