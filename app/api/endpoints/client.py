from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
from typing import Optional, List
from pydantic import BaseModel
from pathlib import Path

from app.core.database import get_db
from app.models.models import Subscription
from app.core.config import settings

router = APIRouter()
CACHE_DIR = Path(settings.SHARED_CACHE_DIR)

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
        
    # Return data from shared cache
    file_path = CACHE_DIR / "market_snap" / "market_activity.csv"
    if file_path.exists():
        return FileResponse(file_path, media_type="text/csv", filename="market_activity.csv")
    
    raise HTTPException(status_code=404, detail="Market activity data not yet available")

@router.get("/data/sse-summary")
def get_sse_summary():
    """
    Get cached SSE summary data. Public endpoint, no token required.
    """
    file_path = CACHE_DIR / "market_snap" / "sse_summary.csv"
    if file_path.exists():
        return FileResponse(file_path, media_type="text/csv", filename="sse_summary.csv")
    
    raise HTTPException(status_code=404, detail="SSE summary data not yet available")

@router.post("/data/realtime-stocks")
def get_realtime_stocks(request: RealtimeStocksRequest):
    """
    Get realtime stock data for specific stock codes.
    Returns full market snapshot as CSV (Zero-Copy approach).
    """
    file_path = CACHE_DIR / "market_snap" / "latest_spot.csv"
    if file_path.exists():
        return FileResponse(file_path, media_type="text/csv", filename="market_spot.csv")
    
    raise HTTPException(status_code=404, detail="Realtime market data not yet available")

@router.get("/data/kline/{stock_code}")
def get_kline_data(
    stock_code: str,
    period: str = Query("daily", description="Period type: daily, weekly, monthly"),
    adjust: str = Query("qfq", description="Adjustment type: qfq, hfq, or empty"),
    days: int = Query(60, description="Number of days to fetch")
):
    """
    Get K-line data for a specific stock from shared cache.
    """
    file_path = CACHE_DIR / "kline_daily" / f"full_{stock_code}.csv"
    if not file_path.exists():
        file_path = CACHE_DIR / "kline_daily" / f"{stock_code}.csv"
        
    if file_path.exists():
        return FileResponse(file_path, media_type="text/csv", filename=f"{stock_code}_kline.csv")
        
    raise HTTPException(status_code=404, detail=f"K-line data for {stock_code} not found")

@router.post("/data/watch-stocks")
def manage_watched_stocks(request: RealtimeStocksRequest):
    """
    Update the list of stocks to watch.
    In the new architecture, this endpoint is deprecated.
    """
    return {
        "message": "Watch list management is no longer required. Full market data is available via /data/realtime-stocks",
        "watched_stocks": request.stock_codes
    }
