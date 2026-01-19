"""
Stock Data Manager Service
Manages all stock data in memory with file backup support
"""
import akshare as ak
import pandas as pd
import logging
import threading
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
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
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
        
        logger.info(f"StockDataManager initialized with data directory: {self.data_dir}")
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.data_dir / "stock_list",
            self.data_dir / "kline_daily",
            self.data_dir / "kline_realtime",
            self.data_dir / "fund_flow",
            self.data_dir / "stock_changes",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Data directories ensured at {self.data_dir}")
    
    # ==================== Stock List Management ====================
    
    def load_stock_list(self) -> bool:
        """Load stock list from file or fetch from akshare"""
        with self.stock_list_lock:
            try:
                # Try loading from file first
                file_path = self.data_dir / "stock_list" / "stock_info_a_code_name.csv"
                if file_path.exists():
                    self.stock_list = pd.read_csv(file_path)
                    self.stock_list_last_updated = datetime.fromtimestamp(file_path.stat().st_mtime)
                    logger.info(f"Loaded stock list from file: {len(self.stock_list)} stocks")
                    return True
                else:
                    # Fetch from akshare if file doesn't exist
                    return self.fetch_stock_list()
            except Exception as e:
                logger.error(f"Error loading stock list: {e}")
                return False
    
    def fetch_stock_list(self) -> bool:
        """Fetch stock list from akshare"""
        with self.stock_list_lock:
            try:
                logger.info("Fetching stock list from akshare...")
                self.stock_list = ak.stock_info_a_code_name()
                self.stock_list_last_updated = datetime.now()
                
                # Save to file
                file_path = self.data_dir / "stock_list" / "stock_info_a_code_name.csv"
                self.stock_list.to_csv(file_path, index=False, encoding='utf-8-sig')
                
                logger.info(f"Stock list fetched and saved: {len(self.stock_list)} stocks")
                return True
            except Exception as e:
                logger.error(f"Error fetching stock list: {e}")
                return False
    
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """Get stock list"""
        with self.stock_list_lock:
            return self.stock_list.copy() if self.stock_list is not None else None
    
    def get_stock_codes(self) -> List[str]:
        """Get all stock codes"""
        with self.stock_list_lock:
            if self.stock_list is None:
                return []
            return self.stock_list['code'].tolist()
    
    # ==================== Daily K-Line Management ====================
    
    def load_daily_klines(self, days: int = 90) -> int:
        """Load daily K-lines for all stocks from files"""
        with self.kline_daily_lock:
            loaded_count = 0
            kline_dir = self.data_dir / "kline_daily"
            
            for csv_file in kline_dir.glob("*.csv"):
                try:
                    stock_code = csv_file.stem
                    df = pd.read_csv(csv_file)
                    
                    # Keep only the last N days
                    if len(df) > days:
                        df = df.tail(days)
                    
                    self.kline_daily[stock_code] = df
                    self.kline_daily_last_updated[stock_code] = datetime.fromtimestamp(csv_file.stat().st_mtime)
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Error loading daily K-line for {csv_file.stem}: {e}")
            
            logger.info(f"Loaded daily K-lines for {loaded_count} stocks")
            return loaded_count
    
    def fetch_daily_kline(self, stock_code: str, days: int = 90, adjust: str = "qfq") -> bool:
        """Fetch daily K-line for a single stock"""
        try:
            logger.info(f"Fetching daily K-line for {stock_code}...")
            
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                adjust=adjust
            )
            
            # Keep only the last N days
            if len(df) > days:
                df = df.tail(days)
            
            with self.kline_daily_lock:
                self.kline_daily[stock_code] = df
                self.kline_daily_last_updated[stock_code] = datetime.now()
            
            # Save to file
            file_path = self.data_dir / "kline_daily" / f"{stock_code}.csv"
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            logger.info(f"Daily K-line fetched for {stock_code}: {len(df)} records")
            return True
        except Exception as e:
            logger.error(f"Error fetching daily K-line for {stock_code}: {e}")
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
                    # Append today's data
                    result = pd.concat([result, today_kline], ignore_index=True)
            
            return result
    
    def _calculate_today_kline(self, stock_code: str) -> Optional[pd.DataFrame]:
        """Calculate today's K-line from realtime data"""
        with self.kline_realtime_lock:
            realtime_df = self.kline_realtime.get(stock_code)
            if realtime_df is None or len(realtime_df) == 0:
                return None
            
            try:
                # Calculate today's K-line from realtime data
                today_data = {
                    '日期': date.today().strftime('%Y-%m-%d'),
                    '开盘': realtime_df.iloc[0]['最新价'],
                    '收盘': realtime_df.iloc[-1]['最新价'],
                    '最高': realtime_df['最新价'].max(),
                    '最低': realtime_df['最新价'].min(),
                    '成交量': realtime_df['成交量'].sum(),
                    '成交额': realtime_df['成交额'].sum(),
                    '振幅': 0,  # Calculate if needed
                    '涨跌幅': 0,  # Calculate if needed
                    '涨跌额': 0,  # Calculate if needed
                    '换手率': 0,  # Calculate if needed
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

    def fetch_realtime_data(self) -> bool:
        """
        Fetch realtime data for all stocks and split by stock code.
        This should be called every 1 minute during trading hours.
        """
        # Prevent concurrent fetching
        if self.is_fetching_realtime:
            logger.warning("Realtime data fetch already in progress, skipping...")
            return False
        
        self.is_fetching_realtime = True
        
        try:
            logger.info("Fetching realtime market data...")
            
            # Fetch all market data
            df = ak.stock_zh_a_spot_em()
            
            if df is None or len(df) == 0:
                logger.warning("No realtime data fetched")
                return False
            
            # Add timestamp
            df['时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with self.kline_realtime_lock:
                # Split by stock code and append to existing data
                for _, row in df.iterrows():
                    stock_code = row['代码']
                    
                    # Convert row to DataFrame
                    row_df = pd.DataFrame([row])
                    
                    if stock_code in self.kline_realtime:
                        # Append to existing data
                        self.kline_realtime[stock_code] = pd.concat(
                            [self.kline_realtime[stock_code], row_df],
                            ignore_index=True
                        )
                    else:
                        # Create new entry
                        self.kline_realtime[stock_code] = row_df
                
                self.kline_realtime_last_updated = datetime.now()
            
            logger.info(f"Realtime data fetched and split for {len(df)} stocks")
            return True
            
        except Exception as e:
            logger.error(f"Error fetching realtime data: {e}")
            return False
        finally:
            self.is_fetching_realtime = False
    
    def get_realtime_kline(self, stock_code: str) -> Optional[pd.DataFrame]:
        """Get realtime K-line for a stock"""
        with self.kline_realtime_lock:
            df = self.kline_realtime.get(stock_code)
            return df.copy() if df is not None else None
    
    def save_realtime_data_to_file(self):
        """Save today's realtime data to files (call after market close)"""
        with self.kline_realtime_lock:
            try:
                realtime_dir = self.data_dir / "kline_realtime"
                
                for stock_code, df in self.kline_realtime.items():
                    file_path = realtime_dir / f"{stock_code}.csv"
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')
                
                logger.info(f"Saved realtime data for {len(self.kline_realtime)} stocks")
                return True
            except Exception as e:
                logger.error(f"Error saving realtime data: {e}")
                return False
    
    def clear_realtime_data(self):
        """Clear realtime data (call at market open for new trading day)"""
        with self.kline_realtime_lock:
            self.kline_realtime.clear()
            self.kline_realtime_last_updated = None
            logger.info("Cleared realtime data for new trading day")
    
    # ==================== Fund Flow Management ====================
    
    def load_fund_flow(self) -> bool:
        """Load fund flow data from file"""
        with self.fund_flow_lock:
            try:
                file_path = self.data_dir / "fund_flow" / "fund_flow_latest.csv"
                if file_path.exists():
                    self.fund_flow = pd.read_csv(file_path)
                    self.fund_flow_last_updated = datetime.fromtimestamp(file_path.stat().st_mtime)
                    logger.info(f"Loaded fund flow data: {len(self.fund_flow)} records")
                    return True
                return False
            except Exception as e:
                logger.error(f"Error loading fund flow data: {e}")
                return False

    def fetch_fund_flow(self) -> bool:
        """Fetch fund flow data and overwrite existing data"""
        with self.fund_flow_lock:
            try:
                logger.info("Fetching fund flow data...")
                
                self.fund_flow = ak.stock_fund_flow_individual(symbol="即时")
                if self.fund_flow is not None and not self.fund_flow.empty:
                    logger.info(f"Fund flow columns: {self.fund_flow.columns.tolist()}")
                
                self.fund_flow_last_updated = datetime.now()
                
                # Save to file
                file_path = self.data_dir / "fund_flow" / "fund_flow_latest.csv"
                self.fund_flow.to_csv(file_path, index=False, encoding='utf-8-sig')
                
                logger.info(f"Fund flow data fetched: {len(self.fund_flow)} records")
                return True
            except Exception as e:
                logger.error(f"Error fetching fund flow data: {e}")
                return False
    
    def get_fund_flow(self, stock_code: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get fund flow data, optionally filtered by stock code"""
        with self.fund_flow_lock:
            if self.fund_flow is None:
                return None
            
            if stock_code:
                # Check actual column name from logs or debugging
                # Usually it's "代码" or "股票代码"
                if '代码' in self.fund_flow.columns:
                    col_name = '代码'
                elif '股票代码' in self.fund_flow.columns:
                    col_name = '股票代码'
                else:
                    # Fallback or error logging
                    logger.error(f"Cannot filter fund flow: '代码' column not found. Columns: {self.fund_flow.columns.tolist()}")
                    return None

                # Filter by stock code
                # Ensure types match (convert to str)
                self.fund_flow[col_name] = self.fund_flow[col_name].astype(str)
                filtered = self.fund_flow[self.fund_flow[col_name] == str(stock_code)]
                return filtered.copy() if len(filtered) > 0 else None
            
            return self.fund_flow.copy()
    
    # ==================== Stock Changes Management ====================
    
    def load_stock_changes(self) -> bool:
        """Load stock changes data from file"""
        with self.stock_changes_lock:
            try:
                file_path = self.data_dir / "stock_changes" / "stock_changes_latest.csv"
                if file_path.exists():
                    self.stock_changes = pd.read_csv(file_path)
                    self.stock_changes_last_updated = datetime.fromtimestamp(file_path.stat().st_mtime)
                    logger.info(f"Loaded stock changes data: {len(self.stock_changes)} records")
                    return True
                return False
            except Exception as e:
                logger.error(f"Error loading stock changes data: {e}")
                return False

    def fetch_stock_changes(self) -> bool:
        """Fetch stock changes data for all change types and overwrite existing data"""
        with self.stock_changes_lock:
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
                    self.stock_changes = pd.concat(all_changes, ignore_index=True)
                    self.stock_changes_last_updated = datetime.now()
                    
                    # Save to file
                    file_path = self.data_dir / "stock_changes" / "stock_changes_latest.csv"
                    self.stock_changes.to_csv(file_path, index=False, encoding='utf-8-sig')
                    
                    logger.info(f"Stock changes data fetched: {len(self.stock_changes)} records")
                    return True
                else:
                    logger.warning("No stock changes data fetched")
                    return False
                    
            except Exception as e:
                logger.error(f"Error fetching stock changes data: {e}")
                return False
    
    def get_stock_changes(self, stock_code: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get stock changes data, optionally filtered by stock code"""
        with self.stock_changes_lock:
            if self.stock_changes is None:
                return None
            
            if stock_code:
                # Filter by stock code
                filtered = self.stock_changes[self.stock_changes['代码'] == stock_code]
                return filtered.copy() if len(filtered) > 0 else None
            
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
                "last_updated": self.kline_realtime_last_updated.isoformat() if self.kline_realtime_last_updated else None
            },
            "fund_flow": {
                "count": len(self.fund_flow) if self.fund_flow is not None else 0,
                "last_updated": self.fund_flow_last_updated.isoformat() if self.fund_flow_last_updated else None
            },
            "stock_changes": {
                "count": len(self.stock_changes) if self.stock_changes is not None else 0,
                "last_updated": self.stock_changes_last_updated.isoformat() if self.stock_changes_last_updated else None
            }
        }


# Global singleton instance
_stock_data_manager: Optional[StockDataManager] = None
_manager_lock = threading.Lock()


def get_stock_data_manager() -> StockDataManager:
    """Get the global StockDataManager instance"""
    global _stock_data_manager
    
    if _stock_data_manager is None:
        with _manager_lock:
            if _stock_data_manager is None:
                _stock_data_manager = StockDataManager()
    
    return _stock_data_manager
