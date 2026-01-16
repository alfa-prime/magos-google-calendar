import datetime
import asyncio
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core import settings, logger
from app.model.event import EventModel


def get_calendar_service():
    """Авторизация"""
    creds = None
    if settings.TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(settings.TOKEN_FILE, settings.SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Токен устарел, обновляю...")
            try:
                creds.refresh(Request())
                with settings.TOKEN_FILE.open('w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                raise Exception(f"Ошибка обновления токена: {e}")
        else:
            raise Exception("Файл token.json не найден. Запустите auth_init.py")

    return build('calendar', 'v3', credentials=creds)


def _get_time_str(time_obj: dict) -> str | None:
    if not time_obj: return None
    return time_obj.get('dateTime') or time_obj.get('date')


def _parse_to_datetime(time_str: str | None) -> datetime.datetime | None:
    if not time_str: return None
    try:
        return datetime.datetime.fromisoformat(time_str)
    except ValueError:
        try:
            # Если это дата (YYYY-MM-DD), делаем полночь UTC
            dt = datetime.datetime.strptime(time_str, "%Y-%m-%d")
            return dt.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return None


async def fetch_upcoming_events(session: AsyncSession):
    """
    Загружает ВСЕ будущие события и сохраняет их в БД.
    """
    loop = asyncio.get_running_loop()

    # 1. Инициализация сервиса (синхронно, в потоке)
    service = await loop.run_in_executor(None, get_calendar_service)

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    logger.info(f"Start fetching events for: {settings.CALENDAR_ID}")

    # 2. Функция для выкачивания ВСЕХ страниц
    def _fetch_all_pages() -> List[dict]:
        all_items = []
        page_token = None
        while True:
            result = service.events().list(
                calendarId=settings.CALENDAR_ID,
                timeMin=now_utc.isoformat(),
                maxResults=250,  # Оптимальный размер страницы
                singleEvents=True,  # Разворачивать повторяющиеся
                orderBy='startTime',
                pageToken=page_token
            ).execute()

            items = result.get('items', [])
            all_items.extend(items)

            page_token = result.get('nextPageToken')
            if not page_token:
                break
        return all_items

    # Запускаем скачивание в потоке
    google_events = await loop.run_in_executor(None, _fetch_all_pages)
    logger.info(f"Получено {len(google_events)} событий из Google API.")

    if not google_events:
        return []

    # 3. Подготовка данных для БД
    events_to_upsert = []

    for ge in google_events:
        start_str = _get_time_str(ge.get('start'))
        end_str = _get_time_str(ge.get('end'))

        event_dict = {
            "google_event_id": ge['id'],
            "summary": ge.get('summary', 'Без названия'),
            # "description": ge.get('description'),
            "start_time": _parse_to_datetime(start_str),
            "end_time": _parse_to_datetime(end_str),
            "link": ge.get('htmlLink'),
        }
        events_to_upsert.append(event_dict)

    # 4. Массовая вставка (UPSERT)
    # Если google_event_id совпадает, обновляем поля, иначе вставляем новую строку
    stmt = pg_insert(EventModel).values(events_to_upsert)

    stmt = stmt.on_conflict_do_update(
        index_elements=['google_event_id'],  # Ключ для проверки дублей
        set_={
            "summary": stmt.excluded.summary,
            # "description": stmt.excluded.description,
            "start_time": stmt.excluded.start_time,
            "end_time": stmt.excluded.end_time,
            "link": stmt.excluded.link,
            "updated_at": func.now()
        }
    )

    await session.execute(stmt)
    await session.commit()

    logger.info("Синхронизация завершена успешно.")
    return events_to_upsert