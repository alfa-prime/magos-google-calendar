from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlmodel import col
from app.core import check_api_key, get_session
from app.service import fetch_upcoming_events
from app.model import EventModel, EventStatus, EventRead

router = APIRouter(prefix="/events", tags=["Events"], dependencies=[Depends(check_api_key)])


@router.get("/", response_model=List[EventRead])
async def get_events(
        # Если передан (например, new), показывает только события с этим статусом.
        status: Optional[EventStatus] = None,
        # Если False (по умолчанию) и статус не выбран — показывает только активные (new, confirmed, changed).
        # Скрывает отмененные и завершенные.
        # Если True — показывает вообще всё, что есть в базе.
        show_archive: bool = False,
        session: AsyncSession = Depends(get_session)
):
    try:
        # 1. Синхронизация
        await fetch_upcoming_events(session)

        # 2. Выборка
        query = select(EventModel).order_by(EventModel.start_time)

        if status:
            query = query.where(col(EventModel.status) == status)

        if not show_archive and not status:
            query = query.where(
                col(EventModel.status).in_([EventStatus.NEW, EventStatus.CONFIRMED, EventStatus.CHANGED])
            )

        result = await session.execute(query)
        events = result.scalars().all()

        return events

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))