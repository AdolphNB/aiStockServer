import akshare as ak
import logging
import threading
from datetime import datetime
from typing import List, Optional, Set
import pandas as pd

# Global In-Memory Cache
market_data_cache = {
    "market_activity": None,
    "sse_summary": None,
    "realtime_stocks": {},  # Cache for realtime stock data: {stock_code: data}
    "last_updated": None,
    "sse_summary_last_updated": None,
    "realtime_stocks_last_updated": None
}
data_lock = threading.Lock()

# Track which stocks to fetch
watched_stocks: Set[str] = set()
watched_stocks_lock = threading.Lock()

logger = logging.getLogger(__name__)

def clean_dataframe_for_json(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean DataFrame to ensure JSON compliance by replacing NaN/inf values with None
    
    Args:
        df: DataFrame to clean
        
    Returns:
        Cleaned DataFrame
    """
    df_clean = df.replace([float('inf'), float('-inf')], None)
    df_clean = df_clean.where(pd.notna(df_clean), None)
    return df_clean

def add_watched_stock(stock_code: str):
    """Add a stock to the watch list for realtime data fetching."""
    with watched_stocks_lock:
        watched_stocks.add(stock_code)
        logger.info(f"Added {stock_code} to watch list. Total watched: {len(watched_stocks)}")

def remove_watched_stock(stock_code: str):
    """Remove a stock from the watch list."""
    with watched_stocks_lock:
        watched_stocks.discard(stock_code)
        logger.info(f"Removed {stock_code} from watch list. Total watched: {len(watched_stocks)}")

def get_watched_stocks() -> List[str]:
    """Get a copy of the currently watched stocks."""
    with watched_stocks_lock:
        return list(watched_stocks)

def fetch_market_data():
    """
    Fetches market data from akshare and updates the global cache.
    Protected by a lock to ensure thread safety during updates.
    """
    try:
        logger.info(f"Fetching market data at {datetime.now()}")
        
        # 1. Market Activity (Legu) - 赚钱效应
        stock_market_activity_legu_df = ak.stock_market_activity_legu()
        
        # Clean DataFrame and convert to dict for JSON serialization
        df_clean = clean_dataframe_for_json(stock_market_activity_legu_df)
        data = df_clean.to_dict(orient="records")
        
        with data_lock:
            market_data_cache["market_activity"] = data
            market_data_cache["last_updated"] = datetime.now().isoformat()
        
        logger.info("Market data updated successfully.")
        
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")

def fetch_sse_summary():
    """
    Fetches SSE summary data from akshare and updates the global cache.
    Protected by a lock to ensure thread safety during updates.
    """
    try:
        logger.info(f"Fetching SSE summary data at {datetime.now()}")
        
        # Fetch SSE summary data
        stock_sse_summary_df = ak.stock_sse_summary()
        
        # Clean DataFrame and convert to dict for JSON serialization
        df_clean = clean_dataframe_for_json(stock_sse_summary_df)
        data = df_clean.to_dict(orient="records")
        
        with data_lock:
            market_data_cache["sse_summary"] = data
            market_data_cache["sse_summary_last_updated"] = datetime.now().isoformat()
        
        logger.info("SSE summary data updated successfully.")
        
    except Exception as e:
        logger.error(f"Error fetching SSE summary data: {e}")

def fetch_realtime_stock_data(stock_codes: List[str]):
    """
    Fetches realtime stock data for a list of stock codes and updates the global cache.
    Protected by a lock to ensure thread safety during updates.
    
    Args:
        stock_codes: List of stock codes (e.g., ['000001', '600519'])
    """
    if not stock_codes:
        return
    
    try:
        logger.info(f"Fetching realtime stock data for {len(stock_codes)} stocks at {datetime.now()}")
        
        # Fetch spot data for all A-shares
        stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()
        
        # Filter for requested stock codes and convert to dict
        realtime_data = {}
        for code in stock_codes:
            # Find the stock in the dataframe
            stock_row = stock_zh_a_spot_em_df[stock_zh_a_spot_em_df['代码'] == code]
            if not stock_row.empty:
                # Clean the row before converting to dict
                stock_row_clean = clean_dataframe_for_json(stock_row)
                stock_dict = stock_row_clean.iloc[0].to_dict()
                
                # Helper function to safely convert to float, handling None
                def safe_float(value, default=0):
                    if value is None or (isinstance(value, float) and pd.isna(value)):
                        return None
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default
                
                realtime_data[code] = {
                    "code": code,
                    "name": stock_dict.get("名称", ""),
                    "price": safe_float(stock_dict.get("最新价")),
                    "change_percent": safe_float(stock_dict.get("涨跌幅")),
                    "change_amount": safe_float(stock_dict.get("涨跌额")),
                    "volume": safe_float(stock_dict.get("成交量")),
                    "amount": safe_float(stock_dict.get("成交额")),
                    "amplitude": safe_float(stock_dict.get("振幅")),
                    "high": safe_float(stock_dict.get("最高")),
                    "low": safe_float(stock_dict.get("最低")),
                    "open": safe_float(stock_dict.get("今开")),
                    "close_prev": safe_float(stock_dict.get("昨收")),
                    "volume_ratio": safe_float(stock_dict.get("量比")),
                    "turnover_rate": safe_float(stock_dict.get("换手率")),
                    "pe_ratio": safe_float(stock_dict.get("市盈率-动态")),
                    "pb_ratio": safe_float(stock_dict.get("市净率")),
                }
        
        with data_lock:
            market_data_cache["realtime_stocks"] = realtime_data
            market_data_cache["realtime_stocks_last_updated"] = datetime.now().isoformat()
        
        logger.info(f"Realtime stock data updated successfully for {len(realtime_data)} stocks.")
        
    except Exception as e:
        logger.error(f"Error fetching realtime stock data: {e}")

def fetch_stock_kline(stock_code: str, period: str = "daily", adjust: str = "qfq", days: int = 60) -> Optional[list]:
    """
    Fetches K-line data for a single stock.
    
    Args:
        stock_code: Stock code (e.g., '000001')
        period: Period type ('daily', 'weekly', 'monthly')
        adjust: Adjustment type ('qfq' for forward adjustment, 'hfq' for backward, '' for none)
        days: Number of days to fetch (default 60)
    
    Returns:
        List of K-line data dictionaries or None if error
    """
    try:
        logger.info(f"Fetching K-line data for {stock_code}, period={period}, adjust={adjust}")
        
        # Fetch K-line data from akshare
        stock_zh_a_hist_df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period=period,
            adjust=adjust
        )
        
        # Get the last N days
        if len(stock_zh_a_hist_df) > days:
            stock_zh_a_hist_df = stock_zh_a_hist_df.tail(days)
        
        # Clean DataFrame and convert to list of dictionaries
        df_clean = clean_dataframe_for_json(stock_zh_a_hist_df)
        
        # Helper function to safely convert to float, handling None
        def safe_float(value, default=None):
            if value is None or (isinstance(value, float) and pd.isna(value)):
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        kline_data = []
        for _, row in df_clean.iterrows():
            kline_data.append({
                "date": row["日期"],
                "open": safe_float(row["开盘"]),
                "close": safe_float(row["收盘"]),
                "high": safe_float(row["最高"]),
                "low": safe_float(row["最低"]),
                "volume": safe_float(row["成交量"]),
                "amount": safe_float(row["成交额"]),
                "amplitude": safe_float(row["振幅"]) if "振幅" in row else None,
                "change_percent": safe_float(row["涨跌幅"]) if "涨跌幅" in row else None,
                "change_amount": safe_float(row["涨跌额"]) if "涨跌额" in row else None,
                "turnover_rate": safe_float(row["换手率"]) if "换手率" in row else None,
            })
        
        logger.info(f"Fetched {len(kline_data)} K-line records for {stock_code}")
        return kline_data
        
    except Exception as e:
        logger.error(f"Error fetching K-line data for {stock_code}: {e}")
        return None

def get_latest_market_data():
    with data_lock:
        # Return a copy to prevent mutation issues if consumer modifies it
        # deepcopy might be too slow, shallow copy of the dict wrapper is likely enough
        # assuming the inner data list is treated as read-only by consumers
        return market_data_cache.copy()
