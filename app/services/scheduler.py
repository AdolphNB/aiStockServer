from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time, date
import logging

from app.services.fetcher import fetch_market_data, fetch_sse_summary, fetch_realtime_stock_data, get_watched_stocks
from app.services.trading_calendar import get_trading_calendar_service
from app.services.stock_data_manager import get_stock_data_manager

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def is_trading_time():
    """
    Check if current time is within trading hours and is a trading day
    Trading hours: 09:15-11:30, 13:00-15:00 on trading days
    """
    # Check if today is a trading day
    trading_calendar = get_trading_calendar_service()
    if not trading_calendar.is_trading_day(date.today()):
        return False
    
    # Check trading hours (updated to 9:15 start time)
    now = datetime.now().time()
    morning_start = time(9, 15)
    morning_end = time(11, 30)
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)
    
    return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)

def is_market_closed():
    """Check if market has just closed (after 15:00 on trading day)"""
    trading_calendar = get_trading_calendar_service()
    if not trading_calendar.is_trading_day(date.today()):
        return False
    
    now = datetime.now().time()
    return now > time(15, 0) and now < time(15, 35)

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

async def tick_stock_list():
    """
    Fetch stock list (runs weekly on Monday at 9:00)
    """
    manager = get_stock_data_manager()
    manager.fetch_stock_list()
    logger.info("Stock list updated via scheduler")

async def tick_realtime_market_data():
    """
    Fetch realtime market data every 1 minute during trading hours.
    Splits data by stock code and appends to realtime K-line data.
    """
    if is_trading_time():
        manager = get_stock_data_manager()
        success = await manager.fetch_realtime_data()
        if success:
            logger.info("Realtime market data fetched and split successfully")
    else:
        pass

async def tick_fund_flow():
    """
    Fetch fund flow data every 5 minutes during trading hours.
    Overwrites previous data.
    """
    if is_trading_time():
        manager = get_stock_data_manager()
        success = await manager.fetch_fund_flow()
        if success:
            logger.info("Fund flow data fetched successfully")
    else:
        pass

async def tick_stock_changes():
    """
    Fetch stock changes data every 5 minutes during trading hours.
    Overwrites previous data.
    """
    if is_trading_time():
        manager = get_stock_data_manager()
        success = await manager.fetch_stock_changes()
        if success:
            logger.info("Stock changes data fetched successfully")
    else:
        pass

async def tick_market_close_backup():
    """
    Backup data to files after market close (15:30).
    """
    if is_market_closed():
        manager = get_stock_data_manager()
        
        # Save realtime data to files
        manager.save_realtime_data_to_file()
        
        logger.info("Market close backup completed")
    else:
        pass

def start_scheduler():
    # Legacy tasks (keep for backward compatibility)
    scheduler.add_job(tick, 'interval', seconds=60)
    scheduler.add_job(tick_sse_summary, 'interval', seconds=60)
    scheduler.add_job(tick_realtime_stocks, 'interval', seconds=30)
    
    # New tasks for stock data
    # Update stock list every Monday at 9:00
    scheduler.add_job(tick_stock_list, CronTrigger(day_of_week='mon', hour=9, minute=0))
    
    # Fetch realtime market data every 1 minute during trading hours
    scheduler.add_job(tick_realtime_market_data, 'interval', seconds=60)
    
    # Fetch fund flow data every 5 minutes during trading hours
    scheduler.add_job(tick_fund_flow, 'interval', seconds=300)
    
    # Fetch stock changes data every 5 minutes during trading hours
    scheduler.add_job(tick_stock_changes, 'interval', seconds=300)
    
    # Backup data after market close (runs every minute, but only executes after 15:00)
    scheduler.add_job(tick_market_close_backup, 'interval', seconds=60)
    
    scheduler.start()
    logger.info("Scheduler started with new stock data tasks.")

def stop_scheduler():
    """Stop the scheduler gracefully"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
