from typing import Optional

from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()

url = make_url(settings.database_url)
is_async_driver = "async" in url.drivername

engine: AsyncEngine | Engine
AsyncSessionLocal: Optional[async_sessionmaker[AsyncSession]] = None
SessionLocal: Optional[sessionmaker[Session]] = None

if is_async_driver:
    engine = create_async_engine(settings.database_url, future=True, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
else:
    engine = create_engine(settings.database_url, future=True, echo=False)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


async def get_session() -> AsyncSession | Session:
    if AsyncSessionLocal:
        async with AsyncSessionLocal() as session:
            yield session
    else:
        assert SessionLocal is not None
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()


async def init_db() -> None:
    if is_async_driver:
        async with engine.begin() as conn:  # type: ignore[attr-defined]
            await conn.run_sync(Base.metadata.create_all)
    else:
        with engine.begin() as conn:  # type: ignore[assignment]
            Base.metadata.create_all(bind=conn)
