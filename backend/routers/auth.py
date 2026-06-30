import logging

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import get_settings
from core.database import get_db
from core.rate_limit import ip_rate_limit_key, limiter
from core.security import (
    create_user_tokens,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from models.user import AuthResponse, RefreshTokenRequest, UserLogin, UserResponse, UserSignup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
_settings = get_settings()


def _auth_response(user_id: str, name: str, email: str) -> AuthResponse:
    access_token, refresh_token = create_user_tokens(user_id)
    return AuthResponse(
        token=access_token,
        refreshToken=refresh_token,
        user=UserResponse(id=user_id, name=name, email=email),
    )


@router.post("/signup", response_model=AuthResponse)
@limiter.limit(_settings.RATE_LIMIT_AUTH, key_func=ip_rate_limit_key)
async def signup(
    request: Request,
    body: UserSignup,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not body.name or not body.email or not body.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "All fields required"},
        )

    existing = await db["users"].find_one({"email": body.email.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "User already exists"},
        )

    user_doc = {
        "name": body.name.strip(),
        "email": body.email.lower(),
        "password": hash_password(body.password),
    }
    result = await db["users"].insert_one(user_doc)
    user_id = str(result.inserted_id)
    logger.info("User signed up: %s", user_doc["email"])
    return _auth_response(user_id, user_doc["name"], user_doc["email"])


@router.post("/login", response_model=AuthResponse)
@limiter.limit(_settings.RATE_LIMIT_AUTH, key_func=ip_rate_limit_key)
async def login(
    request: Request,
    body: UserLogin,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not body.email or not body.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "All fields required"},
        )

    user = await db["users"].find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Invalid credentials"},
        )

    user_id = str(user["_id"])
    logger.info("User logged in: %s", user["email"])
    return _auth_response(user_id, user["name"], user["email"])


@router.post("/refresh", response_model=AuthResponse)
@limiter.limit(_settings.RATE_LIMIT_AUTH, key_func=ip_rate_limit_key)
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if not body.refreshToken:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Refresh token required"},
        )

    user_id = verify_refresh_token(body.refreshToken)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid refresh token"},
        )

    try:
        user = await db["users"].find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid refresh token"},
        )

    logger.info("Access token refreshed for user %s", user_id)
    return _auth_response(user_id, user["name"], user["email"])
