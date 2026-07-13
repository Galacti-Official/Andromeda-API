from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    email_verified: bool
    avatar: str
    last_login: datetime | None
    created_at: datetime


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class UserCreateResponse(BaseModel):
    success: bool
    message: str
    user: UserPublic


class UserLoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


class UserLoginResponse(BaseModel):
    success: bool
    message: str
    user: UserPublic


class UserLogoutResponse(BaseModel):
    success: bool
    message: str


class UserEditRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class UserChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class UserChangePasswordResponse(BaseModel):
    message: str


class UserSession(BaseModel):
    session_id: str
    is_current_session: bool
    created_at: datetime
    last_used_at: datetime
    browser: str
    os: str
    device_type: str


class UserSessions(BaseModel):
    sessions: list[UserSession]
