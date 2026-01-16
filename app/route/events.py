from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core import check_api_key, get_session
from app.service import list_events, confirm_event_action
from app.model import EventRead, EventStatus

router = APIRouter(prefix="/events", tags=["Events"], dependencies=[Depends(check_api_key)])


@router.get("/", response_model=List[EventRead])
async def get_events_route(
        status: Optional[EventStatus] = None,
        show_archive: bool = False,
        year: Optional[int] = None,
        month: Optional[int] = None,
        session: AsyncSession = Depends(get_session)
):
    try:
        # Логика дефолтных дат:
        # Применяем фильтр по текущему месяцу ТОЛЬКО если это не спец-режим (New/Changed)
        is_todo_mode = status in [EventStatus.NEW, EventStatus.CHANGED]

        if not is_todo_mode and (year is None or month is None):
            now = datetime.now()
            year = now.year
            month = now.month

        # Если is_todo_mode == True, то year/month останутся None,
        # и сервис вернет все записи без фильтрации по дате.

        return await list_events(session, status, show_archive, year, month)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{event_id}/confirm", response_model=EventRead)
async def confirm_event_route(
        event_id: int,
        session: AsyncSession = Depends(get_session)
):
    try:
        event = await confirm_event_action(session, event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Событие не найдено")
        return event
    except Exception as e:
        print(f"Error confirm: {e}")
        raise HTTPException(status_code=500, detail=str(e))