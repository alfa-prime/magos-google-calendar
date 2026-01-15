from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import check_api_key, get_session
from app.service import fetch_upcoming_events

router = APIRouter(prefix="/events", tags=["Events"], dependencies=[Depends(check_api_key)])


@router.get("/")
async def get_events(session: AsyncSession = Depends(get_session)):
    """
    Получает события из Google, кэширует в БД и возвращает результат.
    """
    try:
        events = await fetch_upcoming_events(session)
        return {"data": events, "count": len(events)}
    except Exception as e:
        # В продакшене лучше логировать e, а пользователю отдавать "Internal Error"
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))