import asyncio, json

from uuid import UUID
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from Andromeda.auth.external.user_auth import verify_jwt
from Andromeda.api.errors import AndromedaError
from Andromeda.api.database.redis import redis_client
from Andromeda.api.database.database import get_session
from Andromeda.models.user import User, UserKey
from Andromeda.schemas.user import UserPublic
from Andromeda.schemas.auth import AuthContext
from Andromeda.services.api_key_service import increment_usage
from Andromeda.config import settings


COOKIE_NAME = "session"
MAX_SESSION_AGE = timedelta(days=30)
security = HTTPBearer(auto_error=False)
_background_tasks: set[asyncio.Task] = set()


async def get_session_user(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session)
) -> UserPublic:
    session_id = request.cookies.get(COOKIE_NAME)
    
    if not session_id:
        raise AndromedaError(401, "unauthorized", "Not authenticated")
    
    raw = await redis_client.get(f"session:{session_id}")
    
    if not raw:
        raise AndromedaError(401, "unauthorized", "Not authenticated")
    
    data = json.loads(raw)
    user_id = UUID(data["user_id"])

    if not user_id:
        raise AndromedaError(401, "unauthorized", "Not authenticated")

    created_at = datetime.fromisoformat(data["created_at"])
    if datetime.now(timezone.utc) - created_at > MAX_SESSION_AGE:
        await redis_client.delete(f"session:{session_id}")
        await redis_client.srem(f"user_sessions:{user_id}", session_id) # type: ignore
        raise AndromedaError(401, "unauthorized", "Not authenticated")

    result = await session.exec(select(User).where(User.id == user_id))
    user = result.one_or_none()
    
    if not user or not user.is_active:
        raise AndromedaError(401, "unauthorized", "Not authenticated")

    data["last_used_at"] = datetime.now(timezone.utc).isoformat()

    await redis_client.setex(f"session:{session_id}", 86400, json.dumps(data))

    response.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        path="/",
        domain=".galacti.org" if settings.production else None,
        max_age=86400
    )

    return UserPublic.model_validate(user)


def _track_usage(kid: str) -> None:
    task = asyncio.create_task(increment_usage(kid))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def get_auth_context(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> AuthContext:
    if credentials:
        payload = verify_jwt(credentials.credentials)

        sub_type, _, kid = payload.sub.partition(":")
        if sub_type != "client" or not kid:
            raise AndromedaError(401, "unauthorized", "Not authenticated")

        result = await session.exec(select(UserKey).where(UserKey.kid == kid))
        key = result.one_or_none()
        if key is None or not key.is_active:
            raise AndromedaError(401, "unauthorized", "Not authenticated")

        user = await session.get(User, key.user_id)
        if user is None or not user.is_active:
            raise AndromedaError(401, "unauthorized", "Not authenticated")

        _track_usage(kid)

        return AuthContext(
            user=UserPublic.model_validate(user),
            scopes=set(payload.scopes or []),
            via="api_key",
            kid=kid,
        )

    user = await get_session_user(request, response, session)
    return AuthContext(user=user, scopes=None, via="session")


def require_scopes(scopes: list[str]):
    def check_scopes(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        # Session users are unrestricted; API keys must hold every listed scope.
        if ctx.scopes is not None and not set(scopes) <= ctx.scopes:
            raise AndromedaError(403, "forbidden", "Insufficient permissions")
        return ctx
    return check_scopes
