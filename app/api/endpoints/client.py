from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.models.models import Subscription
from app.services.fetcher import (
    get_latest_market_data, 
    fetch_stock_kline,
    add_watched_stock,
    remove_watched_stock,
    get_watched_stocks
)

router = APIRouter()

# --- Schemas ---
class SubscriptionCreate(BaseModel):
    machine_id: str
    plan_type: str  # "1m", "3m", "6m", "12m"

class SubscriptionResponse(BaseModel):
    token: str
    expiry: datetime

class MarketDataResponse(BaseModel):
    data: dict
    timestamp: Optional[str]

class RealtimeStocksRequest(BaseModel):
    stock_codes: List[str]

class KLineRequest(BaseModel):
    stock_code: str
    period: str = "daily"
    adjust: str = "qfq"
    days: int = 60

# --- Endpoints ---

@router.post("/subscribe", response_model=SubscriptionResponse)
def create_subscription(sub: SubscriptionCreate, db: Session = Depends(get_db)):
    """
    Simulates a subscription process. 
    In a real app, this would happen AFTER payment verification.
    Here we generate a token immediately for demonstration.
    """
    days_map = {
        "1m": 30,
        "3m": 90,
        "6m": 180,
        "12m": 365
    }
    
    if sub.plan_type not in days_map:
        raise HTTPException(status_code=400, detail="Invalid plan type")
    
    # Generate a secure token
    token = secrets.token_urlsafe(32)
    end_date = datetime.now() + timedelta(days=days_map[sub.plan_type])
    
    new_sub = Subscription(
        machine_id=sub.machine_id,
        token=token,
        plan_type=sub.plan_type,
        end_date=end_date,
        is_active=True # Auto-activate for now
    )
    
    try:
        db.add(new_sub)
        db.commit()
        db.refresh(new_sub)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"token": new_sub.token, "expiry": new_sub.end_date}

@router.get("/data/market-activity")
def get_market_activity(token: str, db: Session = Depends(get_db)):
    """
    Get cached market activity data. Requires a valid token.
    """
    # Verify token
    sub = db.query(Subscription).filter(Subscription.token == token).first()
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not sub.is_active:
        raise HTTPException(status_code=403, detail="Subscription inactive")
        
    if sub.end_date < datetime.now():
        raise HTTPException(status_code=403, detail="Subscription expired")
        
    # Return data from global cache
    data = get_latest_market_data()
    if not data or not data.get("market_activity"):
        # If cache is empty (e.g. server restart and no fetch yet), return empty or trigger fetch?
        # For now, return what we have.
        pass
        
    return {
        "timestamp": data.get("last_updated"),
        "data": data.get("market_activity")
    }

@router.get("/data/sse-summary")
def get_sse_summary():
    """
    Get cached SSE summary data. Public endpoint, no token required.
    """
    data = get_latest_market_data()
    return {
        "timestamp": data.get("sse_summary_last_updated"),
        "data": data.get("sse_summary")
    }

@router.post("/data/realtime-stocks")
def get_realtime_stocks(request: RealtimeStocksRequest):
    """
    Get realtime stock data for specific stock codes.
    Returns cached data if available.
    """
    data = get_latest_market_data()
    realtime_stocks = data.get("realtime_stocks", {})
    
    result = {}
    for code in request.stock_codes:
        if code in realtime_stocks:
            result[code] = realtime_stocks[code]
    
    return {
        "timestamp": data.get("realtime_stocks_last_updated"),
        "data": result
    }

@router.get("/data/kline/{stock_code}")
def get_kline_data(
    stock_code: str,
    period: str = Query("daily", description="Period type: daily, weekly, monthly"),
    adjust: str = Query("qfq", description="Adjustment type: qfq, hfq, or empty"),
    days: int = Query(60, description="Number of days to fetch")
):
    """
    Get K-line data for a specific stock.
    This fetches data on-demand (not cached) to ensure freshness.
    """
    kline_data = fetch_stock_kline(stock_code, period, adjust, days)
    
    if kline_data is None:
        raise HTTPException(status_code=500, detail="Failed to fetch K-line data")
    
    return {
        "stock_code": stock_code,
        "period": period,
        "adjust": adjust,
        "data": kline_data
    }

@router.post("/data/watch-stocks")
def manage_watched_stocks(request: RealtimeStocksRequest):
    """
    Update the list of stocks to watch for realtime data.
    This replaces the entire watch list with the provided codes.
    """
    # Get current watched stocks
    current_watched = set(get_watched_stocks())
    new_watched = set(request.stock_codes)
    
    # Add new stocks
    for code in new_watched - current_watched:
        add_watched_stock(code)
    
    # Remove stocks not in the new list
    for code in current_watched - new_watched:
        remove_watched_stock(code)
    
    return {
        "message": "Watch list updated",
        "watched_stocks": list(new_watched)
    }