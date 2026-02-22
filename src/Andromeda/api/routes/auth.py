from fastapi import APIRouter, Depends, HTTPException

from Andromeda.auth.external.user_auth import auth_user_key
from Andromeda.schemas.jwt import JWTResponse, JWTPayload, UserTokenRequest


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=JWTResponse)
async def get_token(request: UserTokenRequest) -> JWTResponse:
    token = await auth_user_key(request.api_key)
    return JWTResponse(access_token=token)