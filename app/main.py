from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqladmin import Admin, ModelView
import logging

from app.core.config import settings
from app.core.database import engine, Base
from app.models.models import Subscription, AdminUser, PaymentOrder
from app.api.endpoints import client, payment, data
# from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.fetcher import fetch_sse_summary
from app.services.stock_data_manager import get_stock_data_manager

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize stock data manager
    logger.info("Initializing stock data manager for API Server...")
    manager = get_stock_data_manager()
    
    # In API mode, we don't fetch data, we just serve from shared_cache
    # But we might want to ensure directories exist
    
    logger.info("Application starting up...")
    yield
    
    # Cleanup on shutdown
    logger.info("Application shutting down...")
    manager.shutdown()
    logger.info("Application shutdown complete.")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Include Routers
# IMPORTANT: Register data.router BEFORE client.router to avoid route conflicts
# data.router has /data/kline/real which would be caught by client.router's /data/kline/{stock_code}
app.include_router(data.router, prefix=settings.API_V1_STR, tags=["Stock Data"])
app.include_router(client.router, prefix=settings.API_V1_STR, tags=["Client"])
app.include_router(payment.router, prefix=f"{settings.API_V1_STR}/payment", tags=["Payment"])

# Admin Interface
admin = Admin(app, engine)

class SubscriptionAdmin(ModelView, model=Subscription):
    column_list = [Subscription.id, Subscription.machine_id, Subscription.plan_type, Subscription.is_active, Subscription.end_date]
    form_columns = [Subscription.machine_id, Subscription.token, Subscription.plan_type, Subscription.is_active, Subscription.end_date] 

class PaymentOrderAdmin(ModelView, model=PaymentOrder):
    column_list = [PaymentOrder.id, PaymentOrder.order_no, PaymentOrder.machine_id, PaymentOrder.plan_type, PaymentOrder.amount, PaymentOrder.payment_status, PaymentOrder.created_at]
    form_columns = [PaymentOrder.order_no, PaymentOrder.machine_id, PaymentOrder.plan_type, PaymentOrder.amount, PaymentOrder.payment_status, PaymentOrder.wechat_transaction_id]
    column_searchable_list = [PaymentOrder.order_no, PaymentOrder.machine_id]

class UserAdmin(ModelView, model=AdminUser):
    column_list = [AdminUser.id, AdminUser.username]

admin.add_view(SubscriptionAdmin)
admin.add_view(PaymentOrderAdmin)
admin.add_view(UserAdmin)

@app.get("/")
def read_root():
    return {"message": "AIStock Remote Server is Running"}

@app.get("/health")
def health_check():
    """Health check endpoint with data status"""
    from app.services.fetcher import get_latest_market_data
    from app.services.trading_calendar import get_trading_calendar_service
    from datetime import date
    
    data = get_latest_market_data()
    trading_calendar = get_trading_calendar_service()
    manager = get_stock_data_manager()
    stock_data_status = manager.get_status()
    
    return {
        "status": "running",
        "port": settings.PORT,
        "has_market_activity": data.get("market_activity") is not None,
        "market_activity_last_updated": data.get("last_updated"),
        "has_sse_summary": data.get("sse_summary") is not None,
        "sse_summary_last_updated": data.get("sse_summary_last_updated"),
        "is_trading_day": trading_calendar.is_trading_day(date.today()),
        "trading_calendar_cache": trading_calendar.get_cache_info(),
        "stock_data": stock_data_status
    }

@app.get("/sse-summary")
def get_sse_summary_root():
    """Get SSE summary data from root path. Public endpoint."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    file_path = Path(settings.SHARED_CACHE_DIR) / "market_snap" / "sse_summary.csv"
    if file_path.exists():
        return FileResponse(file_path, media_type="text/csv", filename="sse_summary.csv")
    return {"message": "SSE summary data not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
