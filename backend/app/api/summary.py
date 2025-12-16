from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from app.schemas.timeline import SummaryResponse
from app.services.summary_service import SummaryService

router = APIRouter()

@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Get the latest rolling summary.
    If no summary exists, attempts to generate one.
    """
    summary = await SummaryService.get_latest_summary(db)
    if not summary:
        summary = await SummaryService.generate_summary(db)
        if not summary:
             raise HTTPException(status_code=404, detail="No content to summarize")
    return summary

@router.post("/summary/refresh", response_model=SummaryResponse)
async def refresh_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Force regenerate the rolling summary based on latest notes.
    """
    summary = await SummaryService.generate_summary(db)
    if not summary:
        raise HTTPException(status_code=404, detail="No notes available to summarize")
    return summary
