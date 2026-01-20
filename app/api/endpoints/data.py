"""
Stock Data API Endpoints
Provides REST API for stock data access
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional
import os
from pathlib import Path
from datetime import datetime
import logging

from app.core.config import settings
from app.services.stock_data_manager import get_stock_data_manager

router = APIRouter()
logger = logging.getLogger(__name__)

CACHE_DIR = Path(settings.SHARED_CACHE_DIR)

@router.get("/data/kline")
async def get_historical_kline(
    symbol: str = Query(..., description="Stock code (e.g., 000001)"),
    include_today: bool = Query(True, description="Include today's K-line calculated from realtime data")
):
    """
    Get historical daily K-line data for a stock.
    Returns CSV file containing last 90 trading days + today's K-line.
    """
    try:
        # File path in shared cache
        file_path = CACHE_DIR / "kline_daily" / f"full_{symbol}.csv"
        
        # If file doesn't exist, we might need to trigger a fetch or check historical
        if not file_path.exists():
            # Fallback to historical only if full not available
            file_path = CACHE_DIR / "kline_daily" / f"{symbol}.csv"
            
        if not file_path.exists():
            # If still not exists, try to trigger fetch through manager (legacy behavior but in API process)
            manager = get_stock_data_manager()
            if await manager.fetch_daily_kline(symbol):
                # After fetch, the manager should have saved it to cache
                manager.save_full_kline_to_cache(symbol)
                file_path = CACHE_DIR / "kline_daily" / f"full_{symbol}.csv"
        
        if file_path.exists():
            return FileResponse(file_path, media_type="text/csv", filename=f"{symbol}_kline.csv")
        
        raise HTTPException(status_code=404, detail=f"K-line data for {symbol} not found")
        
    except Exception as e:
        logger.error(f"Error getting historical K-line for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/kline/real")
async def get_realtime_kline(
    symbol: str = Query(..., description="Stock code (e.g., 000001)")
):
    """
    Get today's realtime minute-level data for a stock.
    """
    try:
        file_path = CACHE_DIR / "realtime" / f"{symbol}.csv"
        
        if file_path.exists():
            return FileResponse(file_path, media_type="text/csv", filename=f"{symbol}_realtime.csv")
        
        raise HTTPException(status_code=404, detail=f"Realtime data for {symbol} not found")
        
    except Exception as e:
        logger.error(f"Error getting realtime K-line for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/fund-flow")
async def get_fund_flow(
    symbol: Optional[str] = Query(None, description="Stock code (optional, returns all if not provided)")
):
    """
    Get fund flow data (资金流向).
    """
    try:
        file_path = CACHE_DIR / "fund_flow" / "latest_flow.csv"
        
        if file_path.exists():
            # If symbol is provided, we might need to filter. 
            # But the goal is "Zero-Copy CSV Transmission". 
            # Filtering requires loading into memory.
            # For now, let's return the whole file if no symbol, 
            # or if symbol is provided, we might have a choice:
            # 1. Return whole file and let client filter (best for performance)
            # 2. Filter here (violates zero-copy)
            
            # The refactor.md says "API 进程不进行数据解析和序列化，仅进行文件流转发"
            # So we should probably just return the whole file or have Fetcher pre-filter (which is impractical for all symbols).
            return FileResponse(file_path, media_type="text/csv", filename="fund_flow.csv")
        
        raise HTTPException(status_code=404, detail="Fund flow data not found")
        
    except Exception as e:
        logger.error(f"Error getting fund flow data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/stock-changes")
async def get_stock_changes(
    symbol: Optional[str] = Query(None, description="Stock code (optional, returns all if not provided)")
):
    """
    Get stock changes data (盘口异动).
    """
    try:
        file_path = CACHE_DIR / "stock_changes" / "latest_changes.csv"
        
        if file_path.exists():
            return FileResponse(file_path, media_type="text/csv", filename="stock_changes.csv")
        
        raise HTTPException(status_code=404, detail="Stock changes data not found")
        
    except Exception as e:
        logger.error(f"Error getting stock changes data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/stock-list")
async def get_stock_list():
    """
    Get list of all stocks (股票列表).
    """
    try:
        file_path = CACHE_DIR / "stock_list" / "stock_info_a_code_name.csv"
        
        if file_path.exists():
            return FileResponse(file_path, media_type="text/csv", filename="stock_list.csv")
        
        raise HTTPException(status_code=404, detail="Stock list not found")
        
    except Exception as e:
        logger.error(f"Error getting stock list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/status")
async def get_data_status():
    """
    Get system data status.
    """
    try:
        # For status, we still need some info. 
        # We can check file timestamps.
        status = {
            "cache_dir": str(CACHE_DIR),
            "files": {}
        }
        
        for folder in ["realtime", "market_snap", "fund_flow", "stock_changes", "stock_list", "kline_daily"]:
            folder_path = CACHE_DIR / folder
            if folder_path.exists():
                files = list(folder_path.glob("*.csv"))
                status["files"][folder] = {
                    "count": len(files),
                    "last_modified": datetime.fromtimestamp(max(f.stat().st_mtime for f in files)).isoformat() if files else None
                }
        
        return {
            "code": 200,
            "message": "System cache status",
            "data": status
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/market-activity")
async def get_market_activity():
    """
    Get market activity data (赚钱效应).
    """
    try:
        file_path = CACHE_DIR / "market_snap" / "market_activity.csv"
        if file_path.exists():
            return FileResponse(file_path, media_type="text/csv", filename="market_activity.csv")
        raise HTTPException(status_code=404, detail="Market activity data not found")
    except Exception as e:
        logger.error(f"Error getting market activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/sse-summary")
async def get_sse_summary():
    """
    Get SSE summary data (上证指数概况).
    """
    try:
        file_path = CACHE_DIR / "market_snap" / "sse_summary.csv"
        if file_path.exists():
            return FileResponse(file_path, media_type="text/csv", filename="sse_summary.csv")
        raise HTTPException(status_code=404, detail="SSE summary data not found")
    except Exception as e:
        logger.error(f"Error getting SSE summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
