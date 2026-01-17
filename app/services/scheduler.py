from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time, date
import logging

from app.services.fetcher import fetch_market_data, fetch_sse_summary, fetch_realtime_stock_data, get_watched_stocks
from app.services.trading_calendar import get_trading_calendar_service

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def is_trading_time():
    """
    Check if current time is within trading hours and is a trading day
    Trading hours: 09:30-11:30, 13:00-15:00 on trading days
    """
    # Check if today is a trading day
    trading_calendar = get_trading_calendar_service()
    if not trading_calendar.is_trading_day(date.today()):
        return False
    
    # Check trading hours
    now = datetime.now().time()
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)
    
    return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)

async def tick():
    """
    Scheduled job to run periodically.
    Checks if it's trading time before fetching.
    """
    if is_trading_time():
        fetch_market_data()
    else:
        # logger.debug("Not trading time, skipping fetch.")
        pass

async def tick_sse_summary():
    """
    Scheduled job to fetch SSE summary data periodically.
    This runs regardless of trading time.
    """
    fetch_sse_summary()

async def tick_realtime_stocks():
    """
    Scheduled job to fetch realtime stock data for watched stocks.
    Only runs during trading hours.
    """
    if is_trading_time():
        watched = get_watched_stocks()
        if watched:
            fetch_realtime_stock_data(watched)
    else:
        # logger.debug("Not trading time, skipping realtime stock fetch.")
        pass

def start_scheduler():
    # Run market data fetch every 60 seconds during trading hours
    scheduler.add_job(tick, 'interval', seconds=60)
    # Run SSE summary fetch every 60 seconds
    scheduler.add_job(tick_sse_summary, 'interval', seconds=60)
    # Run realtime stock data fetch every 30 seconds during trading hours
    scheduler.add_job(tick_realtime_stocks, 'interval', seconds=30)
    scheduler.start()
    logger.info("Scheduler started.")
