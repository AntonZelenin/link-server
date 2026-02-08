from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from mess_message.settings import get_settings

engine = create_async_engine(get_settings().async_db_url)
async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)
