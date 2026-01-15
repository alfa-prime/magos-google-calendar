import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core import settings, logger
from app.model.event import EventModel


def get_calendar_service():
    """Авторизация и создание клиента"""
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
            raise Exception("Файл token.json не найден. Запустите scripts/auth_init.py")

    return build('calendar', 'v3', credentials=creds)


def _get_time_str(time_obj: dict) -> str | None:
    if not time_obj:
        return None
    return time_obj.get('dateTime') or time_obj.get('date')


def _parse_to_datetime(time_str: str | None) -> datetime.datetime | None:
    """Преобразует строку ISO (или YYYY-MM-DD) в datetime."""
    if not time_str:
        return None
    try:
        return datetime.datetime.fromisoformat(time_str)
    except ValueError:
        try:
            dt = datetime.datetime.strptime(time_str, "%Y-%m-%d")
            return dt.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            return None


async def fetch_upcoming_events(session: AsyncSession, max_results=10):
    # 1. Получаем Event Loop
    loop = asyncio.get_running_loop()

    # 2. Запускаем создание сервиса в отдельном потоке (это синхронная операция)
    service = await loop.run_in_executor(None, get_calendar_service)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    logger.info(f"Запрос событий для: {settings.CALENDAR_ID}")

    # Определяем синхронную функцию-обертку.
    # Это позволяет избежать использования lambda и проблем с передачей именованных аргументов.
    def _sync_fetch_google_events():
        return service.events().list(
            calendarId=settings.CALENDAR_ID,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

    # Запускаем обертку в executor'е
    events_result = await loop.run_in_executor(None, _sync_fetch_google_events)

    raw_events = events_result.get('items', [])

    if not raw_events:
        return []

    clean_events_data = []

    for event in raw_events:
        start_str = _get_time_str(event.get('start'))
        end_str = _get_time_str(event.get('end'))

        event_dict = {
            "id": event['id'],
            "summary": event.get('summary', 'Без названия'),
            "description": event.get('description'),
            "start_time": _parse_to_datetime(start_str),
            "end_time": _parse_to_datetime(end_str),
            "link": event.get('htmlLink'),
        }
        clean_events_data.append(event_dict)

    # UPSERT LOGIC
    if clean_events_data:
        stmt = pg_insert(EventModel).values(clean_events_data)

        stmt = stmt.on_conflict_do_update(
            index_elements=['id'],
            set_={
                "summary": stmt.excluded.summary,
                "description": stmt.excluded.description,
                "start_time": stmt.excluded.start_time,
                "end_time": stmt.excluded.end_time,
                "link": stmt.excluded.link,
                "updated_at": func.now()
            }
        )

        await session.execute(stmt)
        await session.commit()

    logger.info(f"Сохранено/Обновлено {len(clean_events_data)} событий в БД.")

    return clean_events_data