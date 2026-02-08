import contextlib
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker, AsyncConnection

from mess_user import settings


class DatabaseSessionManager:
    def __init__(self, host: str):
        self._engine = create_async_engine(host)
        self._session_maker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()

        self._engine = None
        self._session_maker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._session_maker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._session_maker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(settings.get_settings().async_db_url)


async def get_db_session():
    async with sessionmanager.session() as session:
        yield session
