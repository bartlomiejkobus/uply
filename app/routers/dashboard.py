from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.stats import DashboardSummaryResponse
from app.services import stats_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Dashboard summary",
    description="Return a summary of all monitors with their current status, "
    "24-hour uptime percentage, and average response times.",
)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    return await stats_service.get_dashboard_summary(db)
