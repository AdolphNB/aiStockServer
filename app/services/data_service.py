import pandas as pd
import io
import logging
from app.core.config_v2 import settings
from app.db.session import realtime_sync_engine # Using sync engine with pandas for simplicity in this service layer

logger = logging.getLogger("DataService")

class DataService:
    @staticmethod
    def get_realtime_kline_df(code: str, date: str = None):
        """Query SQLite for intraday kline data and return as DataFrame"""
        if date is None:
            date = pd.Timestamp.now().strftime("%Y-%m-%d")
            
        query = f"SELECT time, open, high, low, close, volume FROM intraday_kline WHERE code='{code}' AND date='{date}' ORDER BY time"
        
        try:
            # We use the sync engine here because it works natively with pd.read_sql
            df = pd.read_sql(query, realtime_sync_engine)
            return df
        except Exception as e:
            logger.error(f"Error reading kline for {code}: {e}")
            return pd.DataFrame()

    @staticmethod
    def serialize_df_arrow(df: pd.DataFrame):
        """Serialize a DataFrame to Apache Arrow (Feather) format for Zero-Copy transmit"""
        if df.empty:
            return b""
            
        sink = io.BytesIO()
        # Arrow (Feather) is extremely efficient for DataFrame serialization
        df.to_feather(sink)
        return sink.getvalue()

    @staticmethod
    def serialize_df_parquet(df: pd.DataFrame):
        """Serialize a DataFrame to Parquet format"""
        if df.empty:
            return b""
            
        sink = io.BytesIO()
        df.to_parquet(sink)
        return sink.getvalue()
