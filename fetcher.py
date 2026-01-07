import akshare as ak
import logging
import threading
from datetime import datetime

# Global In-Memory Cache
market_data_cache = {
    "market_activity": None,
    "last_updated": None
}
data_lock = threading.Lock()

logger = logging.getLogger(__name__)

def fetch_market_data():
    """
    Fetches market data from akshare and updates the global cache.
    Protected by a lock to ensure thread safety during updates.
    """
    try:
        logger.info(f"Fetching market data at {datetime.now()}")
        
        # 1. Market Activity (Legu) - 赚钱效应
        stock_market_activity_legu_df = ak.stock_market_activity_legu()
        
        # Convert to dict for JSON serialization
        data = stock_market_activity_legu_df.to_dict(orient="records")
        
        with data_lock:
            market_data_cache["market_activity"] = data
            market_data_cache["last_updated"] = datetime.now().isoformat()
        
        logger.info("Market data updated successfully.")
        
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")

def get_latest_market_data():
    with data_lock:
        # Return a copy to prevent mutation issues if consumer modifies it
        # deepcopy might be too slow, shallow copy of the dict wrapper is likely enough
        # assuming the inner data list is treated as read-only by consumers
        return market_data_cache.copy()
