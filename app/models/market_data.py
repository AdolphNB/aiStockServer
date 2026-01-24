from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime

# Separate Base for Market Data to avoid mixing with operational data
MarketBase = declarative_base()

class IntradayKline(MarketBase):
    """
    Model for 1-minute Intraday K-lines.
    Stored in a dedicated SQLite DB with WAL mode.
    """
    __tablename__ = "intraday_kline"

    # Composite primary key for better performance or just simple columns
    # In SQLite, a proper index on (date, code, time) is essential
    date = Column(String, primary_key=True) # YYYY-MM-DD
    code = Column(String, primary_key=True)
    time = Column(String, primary_key=True) # HH:MM
    
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    
    # Optional: Keep track of when this record was inserted
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_query_kline', 'date', 'code'),
    )
