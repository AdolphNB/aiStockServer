"""
Stock Data API Endpoints
Provides REST API for stock data access
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import pandas as pd
import logging

from app.services.stock_data_manager import get_stock_data_manager

router = APIRouter()
logger = logging.getLogger(__name__)


def dataframe_to_json_response(df: Optional[pd.DataFrame], message: str = "success"):
    """Convert DataFrame to JSON response format"""
    if df is None or len(df) == 0:
        return {
            "code": 404,
            "message": "No data found",
            "data": None
        }
    
    return {
        "code": 200,
        "message": message,
        "data": {
            "columns": df.columns.tolist(),
            "index": df.index.tolist(),
            "data": df.values.tolist()
        }
    }


@router.get("/data/kline")
async def get_historical_kline(
    symbol: str = Query(..., description="Stock code (e.g., 000001)"),
    include_today: bool = Query(True, description="Include today's K-line calculated from realtime data")
):
    """
    Get historical daily K-line data for a stock.
    Returns last 90 trading days + today's K-line (if include_today=True).
    
    **Parameters:**
    - symbol: Stock code (e.g., "000001")
    - include_today: Whether to include today's K-line (default: True)
    
    **Returns:**
    DataFrame format with columns: 日期, 开盘, 收盘, 最高, 最低, 成交量, etc.
    """
    try:
        manager = get_stock_data_manager()
        
        # Get daily K-line data
        df = manager.get_daily_kline(symbol, include_today=include_today)
        
        if df is None:
            # Try fetching if not in cache
            logger.info(f"Daily K-line for {symbol} not in cache, fetching...")
            if manager.fetch_daily_kline(symbol):
                df = manager.get_daily_kline(symbol, include_today=include_today)
        
        return dataframe_to_json_response(df, f"Historical K-line data for {symbol}")
        
    except Exception as e:
        logger.error(f"Error getting historical K-line for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/kline/real")
async def get_realtime_kline(
    symbol: str = Query(..., description="Stock code (e.g., 000001)")
):
    """
    Get today's realtime minute-level data (分时数据) for a stock.
    
    **Parameters:**
    - symbol: Stock code (e.g., "000001")
    
    **Returns:**
    DataFrame format with today's minute-level trading data
    """
    try:
        manager = get_stock_data_manager()
        
        # Get realtime K-line data
        df = manager.get_realtime_kline(symbol)
        
        return dataframe_to_json_response(df, f"Realtime data for {symbol}")
        
    except Exception as e:
        logger.error(f"Error getting realtime K-line for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/fund-flow")
async def get_fund_flow(
    symbol: Optional[str] = Query(None, description="Stock code (optional, returns all if not provided)")
):
    """
    Get fund flow data (资金流向).
    
    **Parameters:**
    - symbol: Stock code (optional). If provided, returns data for that stock only.
    
    **Returns:**
    DataFrame format with fund flow data
    """
    try:
        manager = get_stock_data_manager()
        
        # Get fund flow data
        df = manager.get_fund_flow(symbol)
        
        if symbol:
            message = f"Fund flow data for {symbol}"
        else:
            message = "All fund flow data"
        
        return dataframe_to_json_response(df, message)
        
    except Exception as e:
        logger.error(f"Error getting fund flow data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/stock-changes")
async def get_stock_changes(
    symbol: Optional[str] = Query(None, description="Stock code (optional, returns all if not provided)")
):
    """
    Get stock changes data (盘口异动).
    
    **Parameters:**
    - symbol: Stock code (optional). If provided, returns data for that stock only.
    
    **Returns:**
    DataFrame format with stock changes data
    """
    try:
        manager = get_stock_data_manager()
        
        # Get stock changes data
        df = manager.get_stock_changes(symbol)
        
        if symbol:
            message = f"Stock changes data for {symbol}"
        else:
            message = "All stock changes data"
        
        return dataframe_to_json_response(df, message)
        
    except Exception as e:
        logger.error(f"Error getting stock changes data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/stock-list")
async def get_stock_list():
    """
    Get list of all stocks (股票列表).
    
    **Returns:**
    DataFrame format with stock code and name
    """
    try:
        manager = get_stock_data_manager()
        
        # Get stock list
        df = manager.get_stock_list()
        
        return dataframe_to_json_response(df, "Stock list")
        
    except Exception as e:
        logger.error(f"Error getting stock list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/status")
async def get_data_status():
    """
    Get system data status.
    
    **Returns:**
    Status information for all data types
    """
    try:
        manager = get_stock_data_manager()
        status = manager.get_status()
        
        return {
            "code": 200,
            "message": "System status",
            "data": status
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
