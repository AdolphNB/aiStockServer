import time
import logging
import traceback
import sys
import os
from datetime import datetime
from func_timeout import func_timeout, FunctionTimedOut

# Add current directory to path so we can import app
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.core.config_v2 import settings
from app.db.session import init_market_db
from app.services.fetcher_engine import fetch_market_snapshot, process_snapshot_to_kline, save_kline_batch

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
    
    logger.info("Starting Fetcher Daemon Loop...")
    
    while True:
        try:
            start_time = time.time()
            
            # Use func_timeout to prevent hanging (120s as requested by user)
            try:
                # Wrap the logic in func_timeout to guarantee termination
                func_timeout(120, single_fetch_cycle)
            except FunctionTimedOut:
                logger.error("FETCH TIMED OUT! Akshare call took longer than 120s. Will retry next minute.")
            except Exception as e:
                logger.error(f"Error in fetch cycle: {e}")
                logger.error(traceback.format_exc())
            
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
