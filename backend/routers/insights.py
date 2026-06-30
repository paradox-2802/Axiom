from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.database import get_db
from middleware.auth import get_current_user_id
from services.analysis_service import (
    generate_risks,
    generate_summary,
    get_cached_risks,
    get_cached_summary,
)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/{chat_id}/summary")
async def get_executive_summary(
    chat_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await get_cached_summary(db, user_id=user_id, chat_id=chat_id)


@router.post("/{chat_id}/summary")
async def create_executive_summary(
    chat_id: str,
    regenerate: bool = Query(default=False),
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await generate_summary(
        db,
        user_id=user_id,
        chat_id=chat_id,
        regenerate=regenerate,
    )


@router.get("/{chat_id}/risks")
async def get_risk_analysis(
    chat_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await get_cached_risks(db, user_id=user_id, chat_id=chat_id)


@router.post("/{chat_id}/risks")
async def create_risk_analysis(
    chat_id: str,
    regenerate: bool = Query(default=False),
    user_id: str = Depends(get_current_user_id),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await generate_risks(
        db,
        user_id=user_id,
        chat_id=chat_id,
        regenerate=regenerate,
    )
