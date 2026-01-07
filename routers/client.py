from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
from typing import Optional
from pydantic import BaseModel

from database import get_db
from models import Subscription
from fetcher import get_latest_market_data

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
