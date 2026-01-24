from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from app.core.config_v2 import settings
from app.models.market_data import MarketBase
import os

# 1. Operational DB (Async) - Subscriptions, Orders
operational_engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=operational_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 2. Market Data DB (Sync Engine for Batch Writes, Async for API reads)
# For the Fetcher (Synchronous batch insert is often more efficient with Pandas)
realtime_sync_engine = create_engine(settings.REALTIME_DB_URL.replace("sqlite+aiosqlite", "sqlite"))

# For the API (Asynchronous read)
realtime_async_engine = create_async_engine(settings.REALTIME_DB_URL, echo=False)

def init_market_db():
    """Initialize market database and tables with WAL mode"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(settings.REALTIME_DB_PATH), exist_ok=True)
    
    # Set WAL mode using sync connection
    with realtime_sync_engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
    
    # Create tables
    MarketBase.metadata.create_all(bind=realtime_sync_engine)

async def get_db():
    """Dependency for operational DB"""
    async with AsyncSessionLocal() as session:
        yield session

async def get_market_db():
    """Dependency for market DB reads"""
    # Simply using the async engine for queries
    return realtime_async_engine
