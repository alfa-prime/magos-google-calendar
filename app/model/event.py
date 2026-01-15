from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Text, func
from sqlmodel import Field, SQLModel


class EventModel(SQLModel, table=True):
    __tablename__ = "events"

    # ID из Google Calendar (строка, первичный ключ)
    # index=True ускорит проверку существования при upsert
    id: str = Field(primary_key=True, index=True)

    summary: str = Field(index=True)

    # sa_type=Text позволяет хранить длинные описания (больше 255 символов)
    description: Optional[str] = Field(default=None, sa_type=Text)

    # sa_column позволяет явно указать тип SQLAlchemy с поддержкой таймзоны
    start_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    end_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    link: Optional[str] = Field(default=None)

    # Время обновления записи в нашей БД (автоматическое)
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
        )
    )