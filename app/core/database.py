from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from app.core import settings

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL, echo=settings.DB_ECHO, future=True
)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

# для создания базы и таблиц, но так как алембик, комментируем
# async def init_db() -> None:
#     async with engine.connect() as conn:
#         async with conn.begin():
#             await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
