from typing import Literal

from pydantic import BaseModel

from Andromeda.schemas.user import UserPublic


class AuthContext(BaseModel):
    user: UserPublic
    scopes: set[str] | None = None  # None = unrestricted (browser session)
    via: Literal["session", "api_key"]
    kid: str | None = None
