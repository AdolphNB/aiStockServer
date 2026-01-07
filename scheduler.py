from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time
import logging

from fetcher import fetch_market_data

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def is_trading_time():
    """
    Simple check for trading hours (09:30-11:30, 13:00-15:00).
    Note: This doesn't account for holidays.
    """
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

def start_scheduler():
    # Run every 60 seconds
    scheduler.add_job(tick, 'interval', seconds=60)
    scheduler.start()
    logger.info("Scheduler started.")
