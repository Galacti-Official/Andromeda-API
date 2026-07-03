import io
import json
import uuid
import user_agents as ua
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps
from sqlmodel import select
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from Andromeda.api.errors import AndromedaError

from Andromeda.auth.hashing import hash_password, verify_password
from Andromeda.auth.external.user_auth import revoke_all_sessions

from Andromeda.models.user import User

from Andromeda.schemas.user import UserCreate, UserPublic, UserEditRequest, UserChangePasswordRequest,  UserChangePasswordResponse, UserSession, UserSessions
from Andromeda.services.email_service import send_verification_email, consume_verification_token

from Andromeda.config import settings


COOKIE_NAME = "session"
MAX_AVATAR_SIZE = 5 * 1024 * 1024
AVATAR_CDN_PREFIX = settings.avatar_cdn_prefix
DEFAULT_AVATAR_URL = settings.default_avatar_url


def _process_and_save_avatar(data: bytes, save_path: Path) -> None:
    try:
        Image.open(io.BytesIO(data)).verify()
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise AndromedaError(400, "bad_request", "File is not a valid image")

    if img.width * img.height > 25_000_000:
        raise AndromedaError(400, "bad_request", "Image resolution too large")

    img = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (512, 512))

    save_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(save_path, "JPEG", quality=90)


def _delete_avatar_file_if_owned(avatar_url: str) -> None:
    if not avatar_url.startswith(AVATAR_CDN_PREFIX) or avatar_url == DEFAULT_AVATAR_URL:
        return

    file_name = Path(avatar_url[len(AVATAR_CDN_PREFIX):]).name
    if not file_name:
        return

    try:
        (Path(settings.avatar_dir) / file_name).unlink(missing_ok=True)
    except OSError:
        pass


async def create_user(request: UserCreate, session: AsyncSession, redis_client) -> UserPublic:
    user = User(
        name = request.name,
        email = request.email,
        password_hash = hash_password(request.password),
        last_login = datetime.now(timezone.utc)
    )

    session.add(user)

    try:
        await session.commit()
        await session.refresh(user)
    except IntegrityError:
        raise AndromedaError(409, "conflict", "A user with this username or email already exists")

    await send_verification_email(str(user.id), user.email, redis_client)

    return UserPublic.model_validate(user)


async def verify_user_email(token: str, session: AsyncSession, redis_client) -> None:
    user_id = await consume_verification_token(token, redis_client)
    if not user_id:
        raise AndromedaError(400, "bad_request", "Invalid or expired verification token")

    result = await session.exec(select(User).where(User.id == user_id))
    user = result.one_or_none()

    if not user:
        raise AndromedaError(404, "not_found", "User not found")

    if user.email_verified:
        return

    user.email_verified = True
    session.add(user)
    await session.commit()


async def request_verification_email(user: UserPublic, redis_client) -> None:
    await send_verification_email(str(user.id), user.email, redis_client)
    

async def delete_user(user: UserPublic, session: AsyncSession, redis_client) -> None:
    result = await session.exec(select(User).where(User.id == user.id))
    selected_user = result.one_or_none()

    if selected_user is None:
        raise AndromedaError(404, "not_found", "Selected user not found")

    await revoke_all_sessions(user, redis_client)

    _delete_avatar_file_if_owned(selected_user.avatar)

    await session.delete(selected_user)
    await session.commit()


async def edit_user(request: UserEditRequest, user: UserPublic, session: AsyncSession) -> UserPublic:
    result = await session.exec(select(User).where(User.id == user.id))
    selected_user = result.one_or_none()

    if selected_user is None:
        raise AndromedaError(404, "not_found", "Selected user not found")

    if request.name:
        selected_user.name = request.name

    session.add(selected_user)
    await session.commit()
    await session.refresh(selected_user)

    return UserPublic.model_validate(selected_user)


async def set_user_avatar(avatar: UploadFile, user: UserPublic, session: AsyncSession) -> UserPublic:
    if not avatar.filename:
        raise AndromedaError(400, "bad_request", "No file selected")

    if avatar.size and avatar.size > MAX_AVATAR_SIZE:
        raise AndromedaError(413, "content_too_large", f"File too large, max size {MAX_AVATAR_SIZE} bytes.")
    
    result = await session.exec(select(User).where(User.id == user.id))
    selected_user = result.one_or_none()

    if selected_user is None:
        raise AndromedaError(404, "not_found", "Selected user not found") 
    
    data = bytearray()
    try:
        while chunk := await avatar.read(1024 * 1024): # 1 MB chunk size
            data.extend(chunk)
            if len(data) > MAX_AVATAR_SIZE:
                raise AndromedaError(413, "content_too_large", f"File too large, max size {MAX_AVATAR_SIZE} bytes.")
    finally:
        await avatar.close()

    file_name = f"{uuid.uuid4().hex}.jpg"
    save_path = Path(settings.avatar_dir) / file_name
    await run_in_threadpool(_process_and_save_avatar, bytes(data), save_path)

    old_avatar = selected_user.avatar
    selected_user.avatar = f"{AVATAR_CDN_PREFIX}{file_name}"

    session.add(selected_user)
    await session.commit()
    await session.refresh(selected_user)

    _delete_avatar_file_if_owned(old_avatar)

    return UserPublic.model_validate(selected_user)


async def reset_user_avatar(user: UserPublic, session: AsyncSession) -> UserPublic:
    result = await session.exec(select(User).where(User.id == user.id))
    selected_user = result.one_or_none()

    if selected_user is None:
        raise AndromedaError(404, "not_found", "Selected user not found")

    old_avatar = selected_user.avatar
    selected_user.avatar = DEFAULT_AVATAR_URL

    session.add(selected_user)
    await session.commit()
    await session.refresh(selected_user)

    _delete_avatar_file_if_owned(old_avatar)

    return UserPublic.model_validate(selected_user)
    

async def change_user_password(
    request: UserChangePasswordRequest,
    user: UserPublic,
    session: AsyncSession,
    http_request: Request,
    redis_client,
) -> UserChangePasswordResponse:
    result = await session.exec(select(User).where(User.id == user.id))
    selected_user = result.one_or_none()

    if selected_user is None:
        raise AndromedaError(404, "not_found", "Selected user not found")

    if not selected_user.password_hash:
        raise AndromedaError(400, "bad_request", "Password login is not set up for this account")

    if not verify_password(selected_user.password_hash, request.current_password):
        raise AndromedaError(401, "unauthorized", "Invalid password")

    selected_user.password_hash = hash_password(request.new_password)

    session.add(selected_user)
    await session.commit()

    current_session_id = http_request.cookies.get(COOKIE_NAME)
    await revoke_all_sessions(user, redis_client, except_session_id=current_session_id)

    return UserChangePasswordResponse(message="Password changed successfully")


async def get_user_sessions(user: UserPublic, request: Request, redis_client) -> UserSessions:
    session_ids = await redis_client.smembers(f"user_sessions:{user.id}")
    current_session_id = request.cookies.get(COOKIE_NAME)

    sessions = []

    for session_id in session_ids:
        raw = await redis_client.get(f"session:{session_id}")

        if raw:
            data = json.loads(raw)

            user_agent = ua.parse(data["user_agent"])

            session = UserSession(
                session_id=session_id,
                is_current_session=True if session_id == current_session_id else False,
                created_at=data["created_at"],
                last_used_at=data["last_used_at"],
                browser=user_agent.browser.family,
                os=user_agent.os.family,
                device_type=user_agent.device.family
            )

            sessions.append(session)
        else:
            await redis_client.srem(f"user_sessions:{user.id}", session_id)

    return UserSessions(sessions=sessions)


async def get_user_data(user: UserPublic, session: AsyncSession) -> UserPublic:
    result = await session.exec(select(User).where(User.id == user.id))
    user_data = result.one_or_none()

    if not user_data:
        raise AndromedaError(404, "not_found", "Selected user not found")

    return UserPublic.model_validate(user_data)
