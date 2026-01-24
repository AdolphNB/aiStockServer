import akshare as ak
import pandas as pd
import logging
import time
from datetime import datetime
from app.core.config_v2 import settings
from app.db.session import realtime_sync_engine

logger = logging.getLogger("FetcherEngine")

def fetch_market_snapshot(retries=3, delay=5):
    """
    Fetch full market snapshot from Akshare.
    Includes retry logic for handling transient network errors.
    """
    for i in range(retries):
        try:
            logger.info(f"Fetching data from ak.stock_zh_a_spot_em() (Attempt {i+1}/{retries})...")
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                return df
            logger.warning("Fetched empty data from Akshare.")
        except Exception as e:
            logger.error(f"Error fetching from Akshare (Attempt {i+1}): {e}")
            if i < retries - 1:
                wait = delay * (2 ** i) # Exponential backoff
                logger.info(f"Retrying in {wait} seconds...")
                time.sleep(wait)
            else:
                logger.error("Max retries reached. Fetching failed.")
    return None

def process_snapshot_to_kline(df: pd.DataFrame):
    """Transform snapshot data to 1-minute K-line format"""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    
    # Required columns mapping based on user input
    # 序号 代码 名称 最新价 ... 涨速
    kline_df = pd.DataFrame()
    kline_df['code'] = df['代码']
    kline_df['date'] = today
    kline_df['time'] = current_time
    kline_df['open'] = df['最新价']
    kline_df['high'] = df['最新价']
    kline_df['low'] = df['最新价']
    kline_df['close'] = df['最新价']
    kline_df['volume'] = df['成交量']
    kline_df['created_at'] = now
    
    return kline_df

def save_kline_batch(df: pd.DataFrame):
    """Batch save to SQLite using synchronization engine for speed"""
    if df is None or df.empty:
        return
        
    try:
        # to_sql is very efficient for large batches in WAL mode
        df.to_sql(
            'intraday_kline', 
            con=realtime_sync_engine, 
            if_exists='append', 
            index=False,
            chunksize=5000 # Save all in one or two chunks
        )
        logger.info(f"Successfully saved {len(df)} records to database.")
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
        raise # Re-raise to trigger timeout/retry logic if needed
