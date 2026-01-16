import datetime
import asyncio
from calendar import monthrange
from typing import List, Dict, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func, select, or_

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core import settings, logger
from app.model.event import EventModel, EventStatus


def get_calendar_service():
    """Авторизация"""
    creds = None
    if settings.TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(settings.TOKEN_FILE, settings.SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with settings.TOKEN_FILE.open('w') as token:
                    token.write(creds.to_json())
            except Exception:
                pass
    return build('calendar', 'v3', credentials=creds)


def _get_time_str(time_obj: dict) -> str | None:
    if not time_obj: return None
    return time_obj.get('dateTime') or time_obj.get('date')


def _parse_to_datetime(time_str: str | None) -> datetime.datetime | None:
    if not time_str: return None
    try:
        dt = datetime.datetime.fromisoformat(time_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except ValueError:
        try:
            dt = datetime.datetime.strptime(time_str, "%Y-%m-%d")
            return dt.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return None


async def fetch_upcoming_events(session: AsyncSession, max_results=250):
    loop = asyncio.get_running_loop()
    service = await loop.run_in_executor(None, get_calendar_service)

    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # 1. АРХИВАЦИЯ
    archive_stmt = select(EventModel).where(
        EventModel.end_time < now_utc,
        EventModel.status.in_([EventStatus.NEW, EventStatus.CONFIRMED, EventStatus.CHANGED])
    )
    archive_result = await session.execute(archive_stmt)
    events_to_archive = archive_result.scalars().all()

    for event in events_to_archive:
        if event.status in [EventStatus.NEW, EventStatus.CHANGED]:
            event.status = EventStatus.MISSED
        else:
            event.status = EventStatus.COMPLETED
        session.add(event)

    if events_to_archive:
        await session.commit()
        logger.info(f"В архив: {len(events_to_archive)}")

    # 2. ПОЛУЧЕНИЕ ИЗ GOOGLE
    logger.info(f"Синхронизация: {settings.CALENDAR_ID}")

    def _fetch_all_pages() -> List[dict]:
        all_items = []
        page_token = None
        while True:
            result = service.events().list(
                calendarId=settings.CALENDAR_ID,
                timeMin=now_utc.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token
            ).execute()
            items = result.get('items', [])
            all_items.extend(items)
            page_token = result.get('nextPageToken')
            if not page_token: break
        return all_items

    google_events = await loop.run_in_executor(None, _fetch_all_pages)
    google_ids = {ge['id'] for ge in google_events}

    # 3. СВЕРКА С БД
    stmt = select(EventModel).where(
        or_(
            EventModel.google_event_id.in_(google_ids),
            EventModel.start_time >= now_utc
        )
    )
    result = await session.execute(stmt)
    db_events_map: Dict[str, EventModel] = {e.google_event_id: e for e in result.scalars().all()}

    clean_events_data = []

    # 4. ОБРАБОТКА
    for ge in google_events:
        g_id = ge['id']
        g_summary = ge.get('summary', 'Без названия')
        start_str = _get_time_str(ge.get('start'))
        end_str = _get_time_str(ge.get('end'))

        # Определяем флаг "Весь день" (если есть поле date)
        is_all_day = 'date' in ge.get('start', {})

        event_dict = {
            "google_event_id": g_id,
            "summary": g_summary,
            "start_time": _parse_to_datetime(start_str),
            "end_time": _parse_to_datetime(end_str),
            "link": ge.get('htmlLink'),
            "is_all_day": is_all_day
        }
        clean_events_data.append(event_dict)

        # Логика смены статуса при обновлении
        if g_id in db_events_map:
            event = db_events_map[g_id]

            # Восстанавливаем из отмененных
            if event.status in [EventStatus.CANCELLED, EventStatus.MISSED]:
                # Тут мы не можем просто поменять статус объекта session, так как ниже будет массовый upsert.
                # Но upsert не умеет менять статус условно.
                # Поэтому меняем статус вручную отдельным add
                event.status = EventStatus.NEW
                session.add(event)

            is_changed = (
                    event.summary != g_summary or
                    event.start_time != event_dict['start_time'] or
                    event.end_time != event_dict['end_time']
            )

            if is_changed and event.status == EventStatus.CONFIRMED:
                event.status = EventStatus.CHANGED
                session.add(event)

            db_events_map.pop(g_id)  # Убираем из мапы (останутся только удаленные)

    # 5. UPSERT (Массовая вставка/обновление данных)
    if clean_events_data:
        stmt = pg_insert(EventModel).values(clean_events_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['google_event_id'],
            set_={
                "summary": stmt.excluded.summary,
                "start_time": stmt.excluded.start_time,
                "end_time": stmt.excluded.end_time,
                "link": stmt.excluded.link,
                "is_all_day": stmt.excluded.is_all_day,  # <-- Обновляем флаг
                "updated_at": func.now()
            }
        )
        await session.execute(stmt)

    # 6. УДАЛЕНИЕ (те, что остались в мапе)
    for event in db_events_map.values():
        if event.status not in [EventStatus.CANCELLED, EventStatus.COMPLETED, EventStatus.MISSED]:
            event.status = EventStatus.CANCELLED
            session.add(event)

    await session.commit()
    logger.info(f"Обработано {len(clean_events_data)} событий.")


# --- PUBLIC METHODS ---

async def list_events(
        session: AsyncSession,
        status: Optional[EventStatus] = None,
        show_archive: bool = False,
        year: Optional[int] = None,
        month: Optional[int] = None
) -> Sequence[EventModel]:
    await fetch_upcoming_events(session)
    query = select(EventModel)

    # Фильтр по дате
    if year and month:
        dt_start = datetime.datetime(year, month, 1, tzinfo=datetime.timezone.utc)
        days_in_month = monthrange(year, month)[1]

        if month == 12:
            dt_end = datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
        else:
            dt_end = datetime.datetime(year, month + 1, 1, tzinfo=datetime.timezone.utc)

        query = query.where(
            EventModel.start_time >= dt_start,
            EventModel.start_time < dt_end
        )

    if status:
        query = query.where(EventModel.status == status)
        query = query.order_by(EventModel.start_time.asc())
    elif show_archive:
        archive_statuses = [EventStatus.COMPLETED, EventStatus.MISSED, EventStatus.CANCELLED]
        query = query.where(EventModel.status.in_(archive_statuses))
        query = query.order_by(EventModel.start_time.desc())
    else:
        active_statuses = [EventStatus.NEW, EventStatus.CONFIRMED, EventStatus.CHANGED]
        query = query.where(EventModel.status.in_(active_statuses))
        query = query.order_by(EventModel.start_time.asc())

    result = await session.execute(query)
    return result.scalars().all()


async def confirm_event_action(session: AsyncSession, event_id: int) -> Optional[EventModel]:
    query = select(EventModel).where(EventModel.event_id == event_id)
    result = await session.execute(query)
    event = result.scalar_one_or_none()

    if event:
        event.status = EventStatus.CONFIRMED
        session.add(event)
        await session.commit()
        await session.refresh(event)

    return event