"""
Trading Calendar Service
Provides trading day checking functionality using akshare
"""
import akshare as ak
import logging
from datetime import datetime, date, timedelta
from typing import Set, Optional
import threading

logger = logging.getLogger(__name__)

class TradingCalendarService:
    """
    Trading calendar service using akshare
    Maintains a cache of trading days to avoid frequent API calls
    """
    
    def __init__(self):
        self._trading_days_cache: Set[date] = set()
        self._cache_lock = threading.Lock()
        self._last_update: Optional[datetime] = None
        self._update_interval = timedelta(hours=24)  # Update cache every 24 hours
        
        # Initialize cache on startup
        self._update_cache()
    
    def _update_cache(self):
        """
        Update trading days cache from akshare
        Fetches trading calendar for current year and next year
        """
        try:
            current_year = datetime.now().year
            logger.info(f"Updating trading calendar cache for year {current_year}")
            
            # Get trading calendar for current year
            trade_calendar_df = ak.tool_trade_date_hist_sina()
            
            # Convert to set of dates
            trading_days = set()
            for date_str in trade_calendar_df['trade_date']:
                try:
                    # Parse date string (format: YYYYMMDD or YYYY-MM-DD)
                    if isinstance(date_str, str):
                        if len(date_str) == 8:  # YYYYMMDD
                            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
                        else:  # YYYY-MM-DD or other formats
                            trade_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    else:
                        # If it's already a date/datetime object
                        trade_date = date_str if isinstance(date_str, date) else date_str.date()
                    
                    trading_days.add(trade_date)
                except Exception as e:
                    logger.warning(f"Failed to parse date: {date_str}, error: {e}")
                    continue
            
            with self._cache_lock:
                self._trading_days_cache = trading_days
                self._last_update = datetime.now()
            
            logger.info(f"Trading calendar cache updated: {len(trading_days)} trading days loaded")
            
        except Exception as e:
            logger.error(f"Error updating trading calendar cache: {e}")
            # If update fails, keep existing cache
    
    def _should_update_cache(self) -> bool:
        """Check if cache should be updated"""
        if not self._last_update:
            return True
        return datetime.now() - self._last_update > self._update_interval
    
    def is_trading_day(self, check_date: Optional[date] = None) -> bool:
        """
        Check if a given date is a trading day
        
        Args:
            check_date: Date to check (defaults to today)
        
        Returns:
            True if it's a trading day, False otherwise
        """
        # Update cache if needed
        if self._should_update_cache():
            self._update_cache()
        
        # Default to today
        if check_date is None:
            check_date = date.today()
        
        with self._cache_lock:
            return check_date in self._trading_days_cache
    
    def get_next_trading_day(self, start_date: Optional[date] = None) -> Optional[date]:
        """
        Get the next trading day after the given date
        
        Args:
            start_date: Starting date (defaults to today)
        
        Returns:
            Next trading day or None if not found in cache
        """
        if start_date is None:
            start_date = date.today()
        
        # Update cache if needed
        if self._should_update_cache():
            self._update_cache()
        
        # Search for next trading day (up to 30 days ahead)
        with self._cache_lock:
            for i in range(1, 31):
                next_date = start_date + timedelta(days=i)
                if next_date in self._trading_days_cache:
                    return next_date
        
        return None
    
    def get_previous_trading_day(self, start_date: Optional[date] = None) -> Optional[date]:
        """
        Get the previous trading day before the given date
        
        Args:
            start_date: Starting date (defaults to today)
        
        Returns:
            Previous trading day or None if not found in cache
        """
        if start_date is None:
            start_date = date.today()
        
        # Update cache if needed
        if self._should_update_cache():
            self._update_cache()
        
        # Search for previous trading day (up to 30 days back)
        with self._cache_lock:
            for i in range(1, 31):
                prev_date = start_date - timedelta(days=i)
                if prev_date in self._trading_days_cache:
                    return prev_date
        
        return None
    
    def get_cache_info(self) -> dict:
        """Get information about the cache"""
        with self._cache_lock:
            return {
                "total_trading_days": len(self._trading_days_cache),
                "last_update": self._last_update.isoformat() if self._last_update else None,
                "cache_valid": not self._should_update_cache()
            }


# Global singleton instance
_trading_calendar_service: Optional[TradingCalendarService] = None

def get_trading_calendar_service() -> TradingCalendarService:
    """Get or create the global trading calendar service instance"""
    global _trading_calendar_service
    if _trading_calendar_service is None:
        _trading_calendar_service = TradingCalendarService()
    return _trading_calendar_service
