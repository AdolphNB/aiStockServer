import time
import logging
import traceback
import sys
import os
from datetime import datetime
from pathlib import Path
from func_timeout import func_timeout, FunctionTimedOut

# Add current directory to path so we can import app
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.core.config_v2 import settings
from app.db.session import init_market_db, realtime_sync_engine
from app.services.fetcher_engine import fetch_market_snapshot, process_snapshot_to_kline, save_kline_batch
from app.services.trading_calendar import get_trading_calendar_service
from sqlalchemy import text

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.DATA_DIR / "fetcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FetcherDaemon")

def is_db_empty():
    """Check if the intraday_kline table has any data"""
    try:
        with realtime_sync_engine.connect() as conn:
            # Check if table exists first (basic way)
            result = conn.execute(text("SELECT count(*) FROM intraday_kline")).scalar()
            return result == 0
    except Exception:
        return True # Assume empty if table doesn't exist yet

def single_fetch_cycle():
    """Perform one complete fetch and save cycle"""
    logger.info("--- Cycle Start ---")
    
    # 1. Fetch
    df = fetch_market_snapshot()
    if df is not None:
        # 2. Process
        kline_df = process_snapshot_to_kline(df)
        # 3. Save
        save_kline_batch(kline_df)
    
    logger.info("--- Cycle End ---")

def main():
    logger.info("Initializing Market Database...")
    init_market_db()
    
    calendar = get_trading_calendar_service()
    
    # Check if DB is empty OR if we don't have basic cache data
    should_fetch_initial = False
    
    # 1. Check if database is empty
    if is_db_empty():
        logger.info("Database is empty, will perform initial data fetch.")
        should_fetch_initial = True
    
    # 2. Check if cache files exist (for clients to use)
    cache_dir = settings.SHARED_CACHE_DIR
    stock_list_file = cache_dir / "stock_list" / "stock_info_a_code_name.csv"
    sse_summary_file = cache_dir / "market_snap" / "sse_summary.csv"
    
    if not stock_list_file.exists() or not sse_summary_file.exists():
        logger.info("Basic cache files missing, will perform initial data fetch.")
        should_fetch_initial = True
    
    # 3. Perform initial fetch if needed
    if should_fetch_initial:
        logger.info("Performing initial data fetch to ensure clients have baseline data...")
        try:
            func_timeout(120, single_fetch_cycle)
            logger.info("Initial data fetch completed successfully.")
        except Exception as e:
            logger.error(f"Initial fetch failed: {e}")
            logger.warning("Continuing anyway, will retry on next cycle if in trading hours.")

    logger.info("Starting Fetcher Daemon Loop...")
    
    while True:
        try:
            start_time = time.time()
            
            # Trading Session Check
            is_trade_day = calendar.is_trading_day()
            is_trade_hour = calendar.is_trading_hour()
            
            if is_trade_day and is_trade_hour:
                # Use func_timeout to prevent hanging (120s as requested by user)
                try:
                    # Wrap the logic in func_timeout to guarantee termination
                    func_timeout(120, single_fetch_cycle)
                except FunctionTimedOut:
                    logger.error("FETCH TIMED OUT! Akshare call took longer than 120s. Will retry next minute.")
                except Exception as e:
                    logger.error(f"Error in fetch cycle: {e}")
                    logger.error(traceback.format_exc())
            else:
                reason = "Not a trading day" if not is_trade_day else "Not within trading hours"
                logger.info(f"Skipping fetch: {reason}.")
            
            # Align to next minute
            elapsed = time.time() - start_time
            sleep_time = max(0, 60 - elapsed)
            
            if sleep_time > 0:
                logger.info(f"Sleeping for {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                logger.warning(f"Cycle took {elapsed:.2f}s, exceeding 60s bucket.")
                
        except KeyboardInterrupt:
            logger.info("Stop signal received. Gracefully exiting...")
            break
        except Exception as e:
            # Absolute level catch-all
            logger.critical(f"UNRECOVERABLE CRITICAL ERROR IN LOOP: {e}")
            time.sleep(10) # Wait a bit before retry in case of severe system issues

if __name__ == "__main__":
    main()
