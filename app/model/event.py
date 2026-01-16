import uuid
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

    # Внутренний ID (Primary Key)
    event_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, Identity(always=True), primary_key=True)
    )

    # Google ID
    google_event_id: str = Field(unique=True, index=True)

    status: EventStatus = Field(default=EventStatus.NEW, index=True)
    summary: str = Field(index=True)

    # Флаг "Весь день"
    is_all_day: bool = Field(default=False)

    link: Optional[str] = Field(default=None)

    # Время
    start_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )
    end_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        )
    )


# Схема для ответа API
class EventRead(SQLModel):
    event_id: int
    google_event_id: str
    status: EventStatus
    summary: str
    is_all_day: bool
    link: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    updated_at: datetime