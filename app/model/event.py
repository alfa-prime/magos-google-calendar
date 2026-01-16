from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Text, func, BigInteger, Identity
from sqlmodel import Field, SQLModel


class EventStatus(str, Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    CHANGED = "changed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    MISSED = "missed"


class EventModel(SQLModel, table=True):
    __tablename__ = "events"

    event_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True)
    )

    # ID из Google (для поиска дублей)
    google_event_id: str = Field(unique=True, index=True)

    # Статус (по умолчанию NEW)
    status: EventStatus = Field(default=EventStatus.NEW, index=True)

    summary: str = Field(index=True)

    # Описание может быть длинным/пустым
    # description: Optional[str] = Field(default=None, sa_type=Text)

    # Время с часовым поясом
    start_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    end_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    link: Optional[str] = Field(default=None)

    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        )
    )


# СХЕМА ДЛЯ ОТВЕТА API (Response)
class EventRead(SQLModel):
    """
    То, что видит фронтенд.
    """
    event_id: int
    google_event_id: str
    status: EventStatus
    summary: str
    link: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    updated_at: datetime
