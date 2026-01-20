import os
import time
import logging
import asyncio
from pathlib import Path
from datetime import datetime, time as dt_time, date

from app.core.config import settings
from app.services.stock_data_manager import get_stock_data_manager
from app.services.trading_calendar import get_trading_calendar_service
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FetcherEngine")

class FetcherEngine:
    def __init__(self):
        self.manager = get_stock_data_manager()
        self.scheduler = AsyncIOScheduler()
        self.trading_calendar = get_trading_calendar_service()

    def is_trading_time(self):
        """Check if current time is within trading hours and is a trading day"""
        if not self.trading_calendar.is_trading_day(date.today()):
            return False
        
        now = datetime.now().time()
        morning_start = dt_time(9, 15)
        morning_end = dt_time(11, 30)
        afternoon_start = dt_time(13, 0)
        afternoon_end = dt_time(15, 0)
        
        return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)

    def is_market_closed(self):
        """Check if market has just closed"""
        if not self.trading_calendar.is_trading_day(date.today()):
            return False
        now = datetime.now().time()
        return now > dt_time(15, 0) and now < dt_time(15, 35)

    async def tick_stock_list(self):
        """Weekly update of stock list"""
        logger.info("Updating stock list...")
        await self.manager.fetch_stock_list()

    async def tick_realtime_market_data(self):
        """Fetch realtime market data every minute"""
        if self.is_trading_time():
            logger.info("Fetching realtime market data...")
            await self.manager.fetch_realtime_data()
        else:
            logger.debug("Not trading time, skipping realtime fetch.")

    async def tick_fund_flow(self):
        """Fetch fund flow data every 5 minutes"""
        if self.is_trading_time():
            logger.info("Fetching fund flow data...")
            await self.manager.fetch_fund_flow()

    async def tick_stock_changes(self):
        """Fetch stock changes data every 5 minutes"""
        if self.is_trading_time():
            logger.info("Fetching stock changes data...")
            await self.manager.fetch_stock_changes()

    async def tick_market_close_backup(self):
        """Backup data after market close"""
        if self.is_market_closed():
            logger.info("Market closed, running backup...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.manager.save_realtime_data_to_file)

    async def tick_market_data(self):
        """Fetch general market data (market activity and sse summary)"""
        logger.info("Fetching market general data...")
        await self.manager.fetch_market_activity()
        await self.manager.fetch_sse_summary()

    def start(self):
        logger.info("Starting Fetcher Engine Scheduler...")
        
        # Initial fetch
        asyncio.create_task(self.tick_stock_list())
        asyncio.create_task(self.tick_market_data())
        
        # Add jobs
        self.scheduler.add_job(self.tick_stock_list, CronTrigger(day_of_week='mon', hour=9, minute=0))
        self.scheduler.add_job(self.tick_market_data, 'interval', seconds=60)
        self.scheduler.add_job(self.tick_realtime_market_data, 'interval', seconds=60)
        self.scheduler.add_job(self.tick_fund_flow, 'interval', seconds=300)
        self.scheduler.add_job(self.tick_stock_changes, 'interval', seconds=300)
        self.scheduler.add_job(self.tick_market_close_backup, 'interval', seconds=60)
        
        self.scheduler.start()
        
    async def run_forever(self):
        self.start()
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.scheduler.shutdown()
            self.manager.shutdown()

if __name__ == "__main__":
    engine = FetcherEngine()
    asyncio.run(engine.run_forever())
