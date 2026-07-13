import secrets

from fastapi import Request, Response

from Andromeda.api.errors import AndromedaError
from Andromeda.config import settings


STATE_COOKIE_NAME = "oauth_state"
STATE_TTL_SECONDS = 300


async def generate_oauth_state(response: Response, redis_client) -> str:
    state = secrets.token_urlsafe(32)
    await redis_client.setex(f"oauth_state:{state}", STATE_TTL_SECONDS, "1")

    response.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        path="/",
        max_age=STATE_TTL_SECONDS,
    )
    return state


async def validate_oauth_state(request: Request, response: Response, state: str, redis_client) -> None:
    cookie_state = request.cookies.get(STATE_COOKIE_NAME)
    response.delete_cookie(STATE_COOKIE_NAME, path="/")

    deleted = await redis_client.delete(f"oauth_state:{state}")
    if not deleted or not cookie_state or not secrets.compare_digest(cookie_state, state):
        raise AndromedaError(400, "bad_request", "Invalid or expired OAuth state")
