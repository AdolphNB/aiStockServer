"""
Stock Data Manager Service
Manages all stock data in memory with file backup support
"""
import akshare as ak
import pandas as pd
import logging
import threading
import asyncio
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional, List
import json

logger = logging.getLogger(__name__)


class StockDataManager:
    """
    Centralized manager for all stock data.
    Keeps data in memory for fast access and provides file backup functionality.
    """
    
    def __init__(self, data_dir: str = "data", cache_dir: str = "shared_cache"):
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        self._ensure_directories()
        
        # Thread locks for data safety
        self.stock_list_lock = threading.RLock()
        self.kline_daily_lock = threading.RLock()
        self.kline_realtime_lock = threading.RLock()
        self.fund_flow_lock = threading.RLock()
        self.stock_changes_lock = threading.RLock()
        
        # In-memory data storage
        self.stock_list: Optional[pd.DataFrame] = None
        self.kline_daily: Dict[str, pd.DataFrame] = {}  # {stock_code: daily_kline_df}
        self.kline_realtime: Dict[str, pd.DataFrame] = {}  # {stock_code: realtime_kline_df}
        self.fund_flow: Optional[pd.DataFrame] = None
        self.stock_changes: Optional[pd.DataFrame] = None
        
        # Metadata
        self.stock_list_last_updated: Optional[datetime] = None
        self.kline_daily_last_updated: Dict[str, datetime] = {}
        self.kline_realtime_last_updated: Optional[datetime] = None
        self.fund_flow_last_updated: Optional[datetime] = None
        self.stock_changes_last_updated: Optional[datetime] = None
        
        # Flag to prevent concurrent fetching
        self.is_fetching_realtime = False
        self.is_fetching_fund_flow = False
        self.is_fetching_stock_changes = False
        
        # Thread pool for blocking IO operations
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="stock_data_fetch")
        
        logger.info(f"StockDataManager initialized with data directory: {self.data_dir} and cache directory: {self.cache_dir}")
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.data_dir / "stock_list",
            self.data_dir / "kline_daily",
            self.data_dir / "kline_realtime",
            self.data_dir / "fund_flow",
            self.data_dir / "stock_changes",
            # Shared cache directories
            self.cache_dir / "realtime",
            self.cache_dir / "market_snap",
            self.cache_dir / "fund_flow",
            self.cache_dir / "stock_changes",
            self.cache_dir / "stock_list",
            self.cache_dir / "kline_daily",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite DB for realtime data
        self.db_path = self.cache_dir / "realtime_cache.db"
        self._init_db()
        
        logger.info(f"Data and cache directories ensured")

    def _init_db(self):
        """Initialize the SQLite database and tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            # Use WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            # Create table for realtime tick data
            # Store data as rows to easily append every minute
            conn.execute("""
                CREATE TABLE IF NOT EXISTS realtime_ticks (
                    code TEXT,
                    price REAL,
                    volume REAL,
                    amount REAL,
                    high REAL,
                    low REAL,
                    open REAL,
                    timestamp TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_code_time ON realtime_ticks (code, timestamp)")
            conn.commit()
            conn.close()
            logger.info(f"SQLite database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing SQLite DB: {e}")

    def _get_db_conn(self):
        """Get a connection to the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        return conn

    def atomic_write_csv(self, df: pd.DataFrame, file_path: Path):
        """Write DataFrame to CSV atomically using a temporary file"""
        tmp_path = file_path.with_suffix(".csv.tmp")
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(tmp_path, index=False, encoding='utf-8-sig')
            # Use os.replace for atomic operation on both Windows and Linux
            os.replace(tmp_path, file_path)
        except Exception as e:
            logger.error(f"Error in atomic_write_csv for {file_path}: {e}")
            if tmp_path.exists():
                try:
                    os.remove(tmp_path)
                except:
                    pass

    async def fetch_market_activity(self) -> bool:
        """Fetch market activity (legu) and save to cache"""
        try:
            logger.info("Fetching market activity (legu)...")
            df = ak.stock_market_activity_legu()
            if df is not None:
                cache_path = self.cache_dir / "market_snap" / "market_activity.csv"
                self.atomic_write_csv(df, cache_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error fetching market activity: {e}")
            return False

    async def fetch_sse_summary(self) -> bool:
        """Fetch SSE summary and save to cache"""
        try:
            logger.info("Fetching SSE summary...")
            df = ak.stock_sse_summary()
            if df is not None:
                cache_path = self.cache_dir / "market_snap" / "sse_summary.csv"
                self.atomic_write_csv(df, cache_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error fetching SSE summary: {e}")
            return False
    
    # ==================== Stock List Management ====================
    
    async def load_stock_list(self) -> bool:
        """Load stock list from file or fetch from akshare (async version)"""
        # Try loading from file first
        file_path = self.data_dir / "stock_list" / "stock_info_a_code_name.csv"
        if file_path.exists():
            try:
                # Reading CSV is relatively fast, but could be offloaded if it becomes very large
                df = pd.read_csv(file_path)
                
                with self.stock_list_lock:
                    self.stock_list = df
                    # Ensure stock code column is formatted as 6-digit string
                    if 'code' in self.stock_list.columns:
                        self.stock_list['code'] = self.stock_list['code'].apply(
                            lambda x: f"{int(x):06d}" if pd.notna(x) else x
                        )
                    
                    self.stock_list_last_updated = datetime.fromtimestamp(file_path.stat().st_mtime)
                    logger.info(f"Loaded stock list from file: {len(self.stock_list)} stocks")
                    return True
            except Exception as e:
                logger.error(f"Error loading stock list from file: {e}")
                # Fall through to fetch if loading fails
        
        # Fetch from akshare if file doesn't exist or loading failed
        return await self.fetch_stock_list()
    
    def _fetch_stock_list_blocking(self) -> Optional[pd.DataFrame]:
        """Blocking function to fetch stock list from akshare"""
        try:
            logger.info("Fetching stock list from akshare...")
            df = ak.stock_info_a_code_name()
            
            # Ensure stock code column is formatted as 6-digit string
            if 'code' in df.columns:
                df['code'] = df['code'].apply(
                    lambda x: f"{int(x):06d}" if pd.notna(x) else x
                )
            return df
        except Exception as e:
            logger.error(f"Error fetching stock list: {e}")
            return None

    async def fetch_stock_list(self) -> bool:
        """Fetch stock list from akshare (async version)"""
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(self._executor, self._fetch_stock_list_blocking)
            
            if df is None:
                return False
                
            with self.stock_list_lock:
                self.stock_list = df
                self.stock_list_last_updated = datetime.now()
                
                # Save to file
                file_path = self.data_dir / "stock_list" / "stock_info_a_code_name.csv"
                self.stock_list.to_csv(file_path, index=False, encoding='utf-8-sig')
                
                # Save to shared cache
                cache_path = self.cache_dir / "stock_list" / "stock_info_a_code_name.csv"
                self.atomic_write_csv(self.stock_list, cache_path)
                
                logger.info(f"Stock list fetched and saved: {len(self.stock_list)} stocks")
                return True
        except Exception as e:
            logger.error(f"Error in async fetch stock list: {e}")
            return False
    
    def _check_and_reload_if_needed(self, file_path: Path, last_updated_attr: str, loader_func):
        """
        Check if file has been modified since last load, and reload if necessary.
        Uses a throttle to avoid excessive file system checks (e.g. max once per 5 seconds).
        """
        try:
            if not file_path.exists():
                return

            # Get current time and last check time
            now = datetime.now()
            last_check_attr = f"_{last_updated_attr}_check_time"
            last_check = getattr(self, last_check_attr, None)
            
            # Throttle: check file system at most once every 5 seconds
            if last_check and (now - last_check).total_seconds() < 5:
                return

            setattr(self, last_check_attr, now)
            
            # Check file modification time
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            last_updated = getattr(self, last_updated_attr)
            
            # If never loaded or file is newer, reload
            if last_updated is None or file_mtime > last_updated:
                logger.info(f"File {file_path.name} updated, reloading...")
                loader_func()
                
        except Exception as e:
            logger.error(f"Error checking reload for {file_path.name}: {e}")

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """Get stock list (auto-reloads if file changed)"""
        # Check if reload needed
        file_path = self.data_dir / "stock_list" / "stock_info_a_code_name.csv"
        # We use a synchronous wrapper for the async loader or just use read_csv directly
        # Since this is a getter, we prefer the simple read_csv approach used in load_stock_list
        # But load_stock_list is async. Let's make a sync version for reloading or reuse logic.
        
        # To avoid async complexity in getter, we implement a simple sync reload here
        def sync_reload():
            try:
                df = pd.read_csv(file_path)
                with self.stock_list_lock:
                    self.stock_list = df
                    if 'code' in self.stock_list.columns:
                        self.stock_list['code'] = self.stock_list['code'].apply(
                            lambda x: f"{int(x):06d}" if pd.notna(x) else x
                        )
                    self.stock_list_last_updated = datetime.fromtimestamp(file_path.stat().st_mtime)
            except Exception as e:
                logger.error(f"Error reloading stock list: {e}")

        self._check_and_reload_if_needed(file_path, "stock_list_last_updated", sync_reload)
        
        with self.stock_list_lock:
            return self.stock_list.copy() if self.stock_list is not None else None
    
    def get_stock_codes(self) -> List[str]:
        """Get all stock codes"""
        # Trigger reload check via get_stock_list
        df = self.get_stock_list()
        if df is None:
            return []
        return df['code'].tolist()
    
    # ==================== Daily K-Line Management ====================
    
    def load_daily_klines(self, days: int = 90) -> int:
        """Load daily K-lines for all stocks from files"""
        with self.kline_daily_lock:
            loaded_count = 0
            kline_dir = self.data_dir / "kline_daily"
            today_str = date.today().strftime('%Y-%m-%d')
            
            for csv_file in kline_dir.glob("*.csv"):
                try:
                    stock_code = csv_file.stem
                    df = pd.read_csv(csv_file)
                    
                    # Keep only the last N days
                    if len(df) > days:
                        df = df.tail(days)
                    
                    # Remove today's data if present (today's data will be calculated from realtime data)
                    if '日期' in df.columns:
                        df['日期'] = df['日期'].astype(str)
                        df = df[df['日期'] != today_str].copy()
                    
                    # Ensure stock code column is formatted as 6-digit string
                    if '股票代码' in df.columns:
                        df['股票代码'] = df['股票代码'].apply(lambda x: f"{int(x):06d}" if pd.notna(x) else stock_code)
                    
                    self.kline_daily[stock_code] = df
                    self.kline_daily_last_updated[stock_code] = datetime.fromtimestamp(csv_file.stat().st_mtime)
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Error loading daily K-line for {csv_file.stem}: {e}")
            
            logger.info(f"Loaded daily K-lines for {loaded_count} stocks (excluding today's data)")
            return loaded_count
    
    def _fetch_daily_kline_blocking(self, stock_code: str, days: int, adjust: str) -> Optional[pd.DataFrame]:
        """Blocking function to fetch daily K-line from akshare"""
        try:
            logger.info(f"Fetching daily K-line for {stock_code}...")
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                adjust=adjust
            )
            return df
        except Exception as e:
            logger.error(f"Error fetching daily K-line for {stock_code}: {e}")
            return None

    async def fetch_daily_kline(self, stock_code: str, days: int = 90, adjust: str = "qfq") -> bool:
        """Fetch daily K-line for a single stock (async version)"""
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                self._executor, 
                self._fetch_daily_kline_blocking, 
                stock_code, 
                days, 
                adjust
            )
            
            if df is None or df.empty:
                return False
            
            # Keep only the last N days
            if len(df) > days:
                df = df.tail(days)
            
            # Remove today's data if present
            if '日期' in df.columns:
                today_str = date.today().strftime('%Y-%m-%d')
                df['日期'] = df['日期'].astype(str)
                df = df[df['日期'] != today_str].copy()
            
            # Ensure stock code column is formatted as 6-digit string
            if '股票代码' in df.columns:
                df['股票代码'] = df['股票代码'].apply(lambda x: f"{int(x):06d}" if pd.notna(x) else stock_code)
            else:
                df.insert(1, '股票代码', stock_code)
            
            with self.kline_daily_lock:
                self.kline_daily[stock_code] = df
                self.kline_daily_last_updated[stock_code] = datetime.now()
            
            # Save to file
            file_path = self.data_dir / "kline_daily" / f"{stock_code}.csv"
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            # Save to shared cache (full K-line)
            cache_path = self.cache_dir / "kline_daily" / f"{stock_code}.csv"
            self.atomic_write_csv(df, cache_path)
            
            logger.info(f"Daily K-line fetched for {stock_code}: {len(df)} records (excluding today)")
            return True
        except Exception as e:
            logger.error(f"Error in async fetch daily K-line for {stock_code}: {e}")
            return False
    
    def get_daily_kline(self, stock_code: str, include_today: bool = True) -> Optional[pd.DataFrame]:
        """Get daily K-line with optional today's data merged"""
        with self.kline_daily_lock:
            df = self.kline_daily.get(stock_code)
            if df is None:
                return None
            
            result = df.copy()
            
            # Merge today's K-line from realtime data
            if include_today:
                today_kline = self._calculate_today_kline(stock_code)
                if today_kline is not None:
                    today_str = date.today().strftime('%Y-%m-%d')
                    
                    # Check if today's date already exists in historical data
                    if '日期' in result.columns:
                        # Ensure date column is string type for comparison
                        result['日期'] = result['日期'].astype(str)
                        
                        # Count how many records have today's date
                        today_count = (result['日期'] == today_str).sum()
                        
                        if today_count > 0:
                            logger.info(f"Removing {today_count} existing record(s) for {today_str} from {stock_code}")
                            # Remove all existing today's data
                            result = result[result['日期'] != today_str].copy()
                    
                    # Append today's calculated data
                    result = pd.concat([result, today_kline], ignore_index=True)
                    logger.debug(f"Appended today's K-line for {stock_code}, total records: {len(result)}")
            
            return result
    
    def _calculate_today_kline(self, stock_code: str) -> Optional[pd.DataFrame]:
        """Calculate today's K-line from realtime data in SQLite"""
        try:
            # Get latest tick from DB
            conn = self._get_db_conn()
            query = "SELECT * FROM realtime_ticks WHERE code = ? ORDER BY timestamp DESC LIMIT 1"
            latest_df = pd.read_sql_query(query, conn, params=(stock_code,))
            conn.close()
            
            if latest_df.empty:
                # Fallback to in-memory if available
                with self.kline_realtime_lock:
                    realtime_df = self.kline_realtime.get(stock_code)
                    if realtime_df is None or len(realtime_df) == 0:
                        return None
                    latest_row = realtime_df.iloc[-1]
            else:
                # Map DB columns back to what the logic expects
                # DB columns: code, price, volume, amount, high, low, open, timestamp
                row = latest_df.iloc[0]
                latest_row = {
                    '今开': row['open'],
                    '最新价': row['price'],
                    '最高': row['high'],
                    '最低': row['low'],
                    '成交量': row['volume'],
                    '成交额': row['amount']
                }
                
            # Extract values
            open_price = latest_row.get('今开', 0)
            close_price = latest_row.get('最新价', 0)
            high_price = latest_row.get('最高', 0)
            low_price = latest_row.get('最低', 0)
            volume = latest_row.get('成交量', 0)
            amount = latest_row.get('成交额', 0)
            amplitude = latest_row.get('振幅', 0)
            change_pct = latest_row.get('涨跌幅', 0)
            change_amt = latest_row.get('涨跌额', 0)
            turnover = latest_row.get('换手率', 0)
            
            # Ensure stock code is 6-digit format
            formatted_code = f"{int(stock_code):06d}" if str(stock_code).isdigit() else str(stock_code)
            
            # Build today's data with consistent column order
            today_data = {
                '日期': date.today().strftime('%Y-%m-%d'),
                '股票代码': formatted_code,
                '开盘': open_price,
                '收盘': close_price,
                '最高': high_price,
                '最低': low_price,
                '成交量': volume,
                '成交额': amount,
                '振幅': amplitude,
                '涨跌幅': change_pct,
                '涨跌额': change_amt,
                '换手率': turnover,
            }
            
            return pd.DataFrame([today_data])
        except Exception as e:
            logger.error(f"Error calculating today's K-line for {stock_code}: {e}")
            return None
    
    # ==================== Realtime K-Line Management ====================
    
    def load_realtime_data(self) -> int:
        """Load realtime data from files"""
        with self.kline_realtime_lock:
            loaded_count = 0
            realtime_dir = self.data_dir / "kline_realtime"
            if not realtime_dir.exists():
                return 0
                
            for csv_file in realtime_dir.glob("*.csv"):
                try:
                    stock_code = csv_file.stem
                    df = pd.read_csv(csv_file)
                    
                    # Ensure stock code column is formatted as 6-digit string
                    if '代码' in df.columns:
                        df['代码'] = df['代码'].apply(lambda x: f"{int(x):06d}" if pd.notna(x) else stock_code)
                    
                    self.kline_realtime[stock_code] = df
                    # Set timestamp to file modification time if not already set
                    if not self.kline_realtime_last_updated:
                        self.kline_realtime_last_updated = datetime.fromtimestamp(csv_file.stat().st_mtime)
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Error loading realtime data for {csv_file.stem}: {e}")
            
            if loaded_count > 0:
                logger.info(f"Loaded realtime data for {loaded_count} stocks")
            return loaded_count

    def _fetch_realtime_data_blocking(self) -> Optional[pd.DataFrame]:
        """
        Blocking function to fetch realtime data from akshare.
        This runs in a thread pool to avoid blocking the event loop.
        """
        try:
            logger.info("Fetching realtime market data...")
            df = ak.stock_zh_a_spot_em()
            
            if df is None or len(df) == 0:
                logger.warning("No realtime data fetched")
                return None
            
            # Ensure stock code column is formatted as 6-digit string
            if '代码' in df.columns:
                df['代码'] = df['代码'].apply(lambda x: f"{int(x):06d}" if pd.notna(x) else x)
            
            # Add timestamp
            df['时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return df
            
        except Exception as e:
            logger.error(f"Error fetching realtime data: {e}")
            return None
    
    async def fetch_realtime_data(self) -> bool:
        """
        Fetch realtime data for all stocks and save to SQLite (async version).
        This should be called every 1 minute during trading hours.
        """
        if self.is_fetching_realtime:
            logger.warning("Realtime data fetch already in progress, skipping...")
            return False
        
        self.is_fetching_realtime = True
        
        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(self._executor, self._fetch_realtime_data_blocking)
            
            if df is None:
                return False
            
            # 1. Atomic write of the full market snapshot (for status/monitoring)
            market_snap_path = self.cache_dir / "market_snap" / "latest_spot.csv"
            self.atomic_write_csv(df, market_snap_path)
            
            # 2. Batch write all records to SQLite in ONE transaction
            # Mapping akshare columns to our DB columns
            # '代码', '最新价', '成交量', '成交额', '最高', '最低', '今开', '时间'
            db_data = df[['代码', '最新价', '成交量', '成交额', '最高', '最低', '今开', '时间']].copy()
            db_data.columns = ['code', 'price', 'volume', 'amount', 'high', 'low', 'open', 'timestamp']
            
            # Perform batch insert
            conn = self._get_db_conn()
            try:
                db_data.to_sql('realtime_ticks', conn, if_exists='append', index=False)
                conn.commit()
            finally:
                conn.close()
            
            # 3. Update memory metadata
            with self.kline_realtime_lock:
                self.kline_realtime_last_updated = datetime.now()
            
            logger.info(f"Realtime data for {len(df)} stocks saved to SQLite.")
            return True
            
        except Exception as e:
            logger.error(f"Error in async fetch realtime data: {e}")
            return False
        finally:
            self.is_fetching_realtime = False

    def get_realtime_kline_from_db(self, stock_code: str) -> Optional[pd.DataFrame]:
        """Get today's realtime tick data for a stock from SQLite"""
        try:
            conn = self._get_db_conn()
            # Ensure code is string for query
            query = "SELECT * FROM realtime_ticks WHERE code = ? ORDER BY timestamp ASC"
            df = pd.read_sql_query(query, conn, params=(stock_code,))
            conn.close()
            
            if df.empty:
                return None
            
            # Map back to Chinese column names for consistency with existing CSV/API format
            df.columns = ['代码', '最新价', '成交量', '成交额', '最高', '最低', '今开', '时间']
            return df
        except Exception as e:
            logger.error(f"Error reading realtime data from DB for {stock_code}: {e}")
            return None

    def get_realtime_kline(self, stock_code: str) -> Optional[pd.DataFrame]:
        """Get realtime K-line for a stock (tries DB first)"""
        # First try to get from the new SQLite cache
        df = self.get_realtime_kline_from_db(stock_code)
        if df is not None:
            return df
            
        # Fallback to in-memory (for data loaded at startup from legacy CSVs)
        with self.kline_realtime_lock:
            df = self.kline_realtime.get(stock_code)
            return df.copy() if df is not None else None
    
    def save_realtime_data_to_file(self):
        """Save today's realtime data from SQLite to files (call after market close)"""
        try:
            realtime_dir = self.data_dir / "kline_realtime"
            realtime_dir.mkdir(parents=True, exist_ok=True)
            
            # Get all unique codes from DB
            conn = self._get_db_conn()
            codes_df = pd.read_sql_query("SELECT DISTINCT code FROM realtime_ticks", conn)
            
            for stock_code in codes_df['code']:
                df = self.get_realtime_kline_from_db(stock_code)
                if df is not None:
                    file_path = realtime_dir / f"{stock_code}.csv"
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            conn.close()
            logger.info(f"Saved realtime data from SQLite to files for {len(codes_df)} stocks")
            return True
        except Exception as e:
            logger.error(f"Error saving realtime data from DB: {e}")
            return False
    
    def clear_realtime_data(self):
        """Clear realtime data (call at market open for new trading day)"""
        with self.kline_realtime_lock:
            self.kline_realtime.clear()
            self.kline_realtime_last_updated = None
            
            # Also clear SQLite table
            try:
                conn = self._get_db_conn()
                conn.execute("DELETE FROM realtime_ticks")
                conn.commit()
                conn.close()
                logger.info("Cleared SQLite realtime_ticks table")
            except Exception as e:
                logger.error(f"Error clearing SQLite table: {e}")
                
            logger.info("Cleared realtime data for new trading day")
    
    # ==================== Fund Flow Management ====================
    
    def load_fund_flow(self) -> bool:
        """Load fund flow data from file"""
        with self.fund_flow_lock:
            try:
                file_path = self.data_dir / "fund_flow" / "fund_flow_latest.csv"
                if file_path.exists():
                    self.fund_flow = pd.read_csv(file_path)
                    
                    # Ensure stock code column is formatted as 6-digit string
                    for col_name in ['代码', '股票代码', 'code']:
                        if col_name in self.fund_flow.columns:
                            self.fund_flow[col_name] = self.fund_flow[col_name].apply(
                                lambda x: f"{int(x):06d}" if pd.notna(x) else x
                            )
                            break
                    
                    self.fund_flow_last_updated = datetime.fromtimestamp(file_path.stat().st_mtime)
                    logger.info(f"Loaded fund flow data: {len(self.fund_flow)} records")
                    return True
                return False
            except Exception as e:
                logger.error(f"Error loading fund flow data: {e}")
                return False

    def _fetch_fund_flow_blocking(self) -> Optional[pd.DataFrame]:
        """
        Blocking function to fetch fund flow data from akshare.
        This runs in a thread pool to avoid blocking the event loop.
        """
        try:
            logger.info("Fetching fund flow data...")
            df = ak.stock_fund_flow_individual(symbol="即时")
            if df is not None and not df.empty:
                logger.info(f"Fund flow columns: {df.columns.tolist()}")
                
                # Ensure stock code column is formatted as 6-digit string
                # Check for common code column names
                for col_name in ['代码', '股票代码', 'code']:
                    if col_name in df.columns:
                        df[col_name] = df[col_name].apply(lambda x: f"{int(x):06d}" if pd.notna(x) else x)
                        break
            return df
        except Exception as e:
            logger.error(f"Error fetching fund flow data: {e}")
            return None
    
    async def fetch_fund_flow(self) -> bool:
        """Fetch fund flow data and overwrite existing data (async version)"""
        # Prevent concurrent fetching
        if self.is_fetching_fund_flow:
            logger.warning("Fund flow data fetch already in progress, skipping...")
            return False
        
        self.is_fetching_fund_flow = True
        
        try:
            # Run blocking fetch in thread pool
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(self._executor, self._fetch_fund_flow_blocking)
            
            if df is None or df.empty:
                return False
            
            with self.fund_flow_lock:
                self.fund_flow = df
                self.fund_flow_last_updated = datetime.now()
                
                # Save to file
                file_path = self.data_dir / "fund_flow" / "fund_flow_latest.csv"
                self.fund_flow.to_csv(file_path, index=False, encoding='utf-8-sig')
                
                # Save to shared cache
                cache_path = self.cache_dir / "fund_flow" / "latest_flow.csv"
                self.atomic_write_csv(self.fund_flow, cache_path)
            
            logger.info(f"Fund flow data fetched: {len(self.fund_flow)} records")
            return True
        except Exception as e:
            logger.error(f"Error in async fetch fund flow data: {e}")
            return False
        finally:
            self.is_fetching_fund_flow = False
    
    def get_fund_flow(self, stock_code: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get fund flow data, optionally filtered by stock code (auto-reloads if file changed)"""
        
        # Check reload
        file_path = self.data_dir / "fund_flow" / "fund_flow_latest.csv"
        
        def sync_reload():
            try:
                with self.fund_flow_lock:
                    self.fund_flow = pd.read_csv(file_path)
                    for col_name in ['代码', '股票代码', 'code']:
                        if col_name in self.fund_flow.columns:
                            self.fund_flow[col_name] = self.fund_flow[col_name].apply(
                                lambda x: f"{int(x):06d}" if pd.notna(x) else x
                            )
                            break
                    self.fund_flow_last_updated = datetime.fromtimestamp(file_path.stat().st_mtime)
            except Exception as e:
                logger.error(f"Error reloading fund flow: {e}")
                
        self._check_and_reload_if_needed(file_path, "fund_flow_last_updated", sync_reload)

        with self.fund_flow_lock:
            if self.fund_flow is None:
                return None
            
            if stock_code:
                # Check actual column name from logs or debugging
                # Usually it's "代码" or "股票代码"
                col_name = None
                if '代码' in self.fund_flow.columns:
                    col_name = '代码'
                elif '股票代码' in self.fund_flow.columns:
                    col_name = '股票代码'
                else:
                    # Try to find a column that looks like code
                    for col in self.fund_flow.columns:
                        if '代码' in col or 'code' in col.lower():
                            col_name = col
                            break
                
                if not col_name:
                    # Fallback or error logging
                    logger.error(f"Cannot filter fund flow: '代码' column not found. Columns: {self.fund_flow.columns.tolist()}")
                    return None

                # Normalize stock code: ensure 6 digits (e.g., "1" -> "000001")
                try:
                    target_code = "{:06d}".format(int(stock_code))
                except ValueError:
                    target_code = str(stock_code)

                # Filter by stock code
                # Ensure dataframe column is string type and padded
                # Use a copy to avoid SettingWithCopyWarning on the original dataframe
                df_copy = self.fund_flow.copy()
                
                # Helper to normalize code in dataframe
                def normalize_code(val):
                    try:
                        return "{:06d}".format(int(val))
                    except (ValueError, TypeError):
                        return str(val)

                df_copy[col_name] = df_copy[col_name].apply(normalize_code)
                
                filtered = df_copy[df_copy[col_name] == target_code]
                return filtered if len(filtered) > 0 else None
            
            return self.fund_flow.copy()
    
    # ==================== Stock Changes Management ====================
    
    def load_stock_changes(self) -> bool:
        """Load stock changes data from file"""
        with self.stock_changes_lock:
            try:
                file_path = self.data_dir / "stock_changes" / "stock_changes_latest.csv"
                if file_path.exists():
                    self.stock_changes = pd.read_csv(file_path)
                    
                    # Ensure stock code column is formatted as 6-digit string
                    for col_name in ['代码', '股票代码', 'code']:
                        if col_name in self.stock_changes.columns:
                            self.stock_changes[col_name] = self.stock_changes[col_name].apply(
                                lambda x: f"{int(x):06d}" if pd.notna(x) else x
                            )
                            break
                    
                    self.stock_changes_last_updated = datetime.fromtimestamp(file_path.stat().st_mtime)
                    logger.info(f"Loaded stock changes data: {len(self.stock_changes)} records")
                    return True
                return False
            except Exception as e:
                logger.error(f"Error loading stock changes data: {e}")
                return False

    def _fetch_stock_changes_blocking(self) -> Optional[pd.DataFrame]:
        """
        Blocking function to fetch stock changes data from akshare.
        This runs in a thread pool to avoid blocking the event loop.
        """
        try:
            logger.info("Fetching stock changes data...")
            
            # List of all change types
            change_types = [
                '火箭发射', '快速反弹', '大笔买入', '打开跌停板', '有大买盘',
                '加速下跌', '高台跳水', '大笔卖出', '打开涨停板', '有大卖盘'
            ]
            
            all_changes = []
            for change_type in change_types:
                try:
                    df = ak.stock_changes_em(symbol=change_type)
                    if df is not None and len(df) > 0:
                        all_changes.append(df)
                except Exception as e:
                    logger.warning(f"Error fetching {change_type}: {e}")
                    continue
            
            if all_changes:
                result_df = pd.concat(all_changes, ignore_index=True)
                
                # Ensure stock code column is formatted as 6-digit string
                for col_name in ['代码', '股票代码', 'code']:
                    if col_name in result_df.columns:
                        result_df[col_name] = result_df[col_name].apply(
                            lambda x: f"{int(x):06d}" if pd.notna(x) else x
                        )
                        break
                
                return result_df
            else:
                logger.warning("No stock changes data fetched")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching stock changes data: {e}")
            return None
    
    async def fetch_stock_changes(self) -> bool:
        """Fetch stock changes data for all change types and overwrite existing data (async version)"""
        # Prevent concurrent fetching
        if self.is_fetching_stock_changes:
            logger.warning("Stock changes data fetch already in progress, skipping...")
            return False
        
        self.is_fetching_stock_changes = True
        
        try:
            # Run blocking fetch in thread pool
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(self._executor, self._fetch_stock_changes_blocking)
            
            if df is None or df.empty:
                return False
            
            with self.stock_changes_lock:
                self.stock_changes = df
                self.stock_changes_last_updated = datetime.now()
                
                # Save to file
                file_path = self.data_dir / "stock_changes" / "stock_changes_latest.csv"
                self.stock_changes.to_csv(file_path, index=False, encoding='utf-8-sig')
                
                # Save to shared cache
                cache_path = self.cache_dir / "stock_changes" / "latest_changes.csv"
                self.atomic_write_csv(self.stock_changes, cache_path)
            
            logger.info(f"Stock changes data fetched: {len(self.stock_changes)} records")
            return True
        except Exception as e:
            logger.error(f"Error in async fetch stock changes data: {e}")
            return False
        finally:
            self.is_fetching_stock_changes = False
    
    def get_stock_changes(self, stock_code: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get stock changes data, optionally filtered by stock code (auto-reloads if file changed)"""
        
        # Check reload
        file_path = self.data_dir / "stock_changes" / "stock_changes_latest.csv"
        
        def sync_reload():
            try:
                with self.stock_changes_lock:
                    self.stock_changes = pd.read_csv(file_path)
                    for col_name in ['代码', '股票代码', 'code']:
                        if col_name in self.stock_changes.columns:
                            self.stock_changes[col_name] = self.stock_changes[col_name].apply(
                                lambda x: f"{int(x):06d}" if pd.notna(x) else x
                            )
                            break
                    self.stock_changes_last_updated = datetime.fromtimestamp(file_path.stat().st_mtime)
            except Exception as e:
                logger.error(f"Error reloading stock changes: {e}")

        self._check_and_reload_if_needed(file_path, "stock_changes_last_updated", sync_reload)

        with self.stock_changes_lock:
            if self.stock_changes is None:
                return None
            
            if stock_code:
                # Ensure correct column name for code
                col_name = '代码' if '代码' in self.stock_changes.columns else 'code'
                if col_name not in self.stock_changes.columns:
                    # Try to find a column that looks like code
                    for col in self.stock_changes.columns:
                        if '代码' in col or 'code' in col.lower():
                            col_name = col
                            break
                
                if col_name not in self.stock_changes.columns:
                    logger.error(f"Cannot filter stock changes: code column not found. Columns: {self.stock_changes.columns.tolist()}")
                    return None

                # Normalize stock code: ensure 6 digits (e.g., "1" -> "000001")
                try:
                    target_code = "{:06d}".format(int(stock_code))
                except ValueError:
                    target_code = str(stock_code)
                
                # Filter by stock code
                # Ensure dataframe column is string type and padded
                # Use a copy to avoid SettingWithCopyWarning on the original dataframe
                df_copy = self.stock_changes.copy()
                
                # Helper to normalize code in dataframe
                def normalize_code(val):
                    try:
                        return "{:06d}".format(int(val))
                    except (ValueError, TypeError):
                        return str(val)

                df_copy[col_name] = df_copy[col_name].apply(normalize_code)
                
                filtered = df_copy[df_copy[col_name] == target_code]
                return filtered if len(filtered) > 0 else None
            
            return self.stock_changes.copy()
    
    # ==================== System Status ====================
    
    def get_status(self) -> Dict:
        """Get system status information"""
        return {
            "stock_list": {
                "count": len(self.stock_list) if self.stock_list is not None else 0,
                "last_updated": self.stock_list_last_updated.isoformat() if self.stock_list_last_updated else None
            },
            "kline_daily": {
                "count": len(self.kline_daily),
                "stocks": list(self.kline_daily.keys())[:10]  # Show first 10
            },
            "kline_realtime": {
                "count": len(self.kline_realtime),
                "last_updated": self.kline_realtime_last_updated.isoformat() if self.kline_realtime_last_updated else None,
                "is_fetching": self.is_fetching_realtime
            },
            "fund_flow": {
                "count": len(self.fund_flow) if self.fund_flow is not None else 0,
                "last_updated": self.fund_flow_last_updated.isoformat() if self.fund_flow_last_updated else None,
                "is_fetching": self.is_fetching_fund_flow
            },
            "stock_changes": {
                "count": len(self.stock_changes) if self.stock_changes is not None else 0,
                "last_updated": self.stock_changes_last_updated.isoformat() if self.stock_changes_last_updated else None,
                "is_fetching": self.is_fetching_stock_changes
            }
        }
    
    def save_full_kline_to_cache(self, stock_code: str):
        """Merge historical and today's K-line and save to shared cache"""
        df = self.get_daily_kline(stock_code, include_today=True)
        if df is not None:
            cache_path = self.cache_dir / "kline_daily" / f"full_{stock_code}.csv"
            self.atomic_write_csv(df, cache_path)
            return True
        return False

    def shutdown(self):
        """Shutdown the manager and cleanup resources"""
        logger.info("Shutting down StockDataManager...")
        self._executor.shutdown(wait=True, cancel_futures=False)
        logger.info("Thread pool executor shutdown complete")


# Global singleton instance
_stock_data_manager: Optional[StockDataManager] = None
_manager_lock = threading.Lock()


def get_stock_data_manager() -> StockDataManager:
    """Get the global StockDataManager instance"""
    global _stock_data_manager
    
    if _stock_data_manager is None:
        with _manager_lock:
            if _stock_data_manager is None:
                from app.core.config import settings
                _stock_data_manager = StockDataManager(
                    data_dir=settings.DATA_DIR,
                    cache_dir=settings.SHARED_CACHE_DIR
                )
    
    return _stock_data_manager
