from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqladmin import Admin, ModelView
import logging

from app.core.config_v2 import settings
from app.db.session import operational_engine
from app.models.models import Subscription, AdminUser, PaymentOrder
from app.api.endpoints import client, payment, data, data_v2 # Loading both for compatibility
from app.services.stock_data_manager import get_stock_data_manager

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    
    # Initialize stock data manager and ensure basic data exists
    logger.info("Initializing stock data manager...")
    manager = get_stock_data_manager()
    
    # Check if we have basic data, if not fetch it
    # This ensures clients can get data even when starting on non-trading days
    logger.info("Checking for initial data availability...")
    await manager.ensure_initial_data()
    
    logger.info("Application startup complete.")
    yield
    
    logger.info("Application shutting down...")
    manager.shutdown()
    logger.info("Application shutdown complete.")

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Include Routers
# V2 Data Router (New High-Performance)
app.include_router(data_v2.router, prefix=settings.API_V1_STR, tags=["Stock Data V2"])

# V1 Legacy Routers
app.include_router(data.router, prefix=settings.API_V1_STR, tags=["Stock Data Legacy"])
app.include_router(client.router, prefix=settings.API_V1_STR, tags=["Client"])
app.include_router(payment.router, prefix=f"{settings.API_V1_STR}/payment", tags=["Payment"])

# Admin Interface
admin = Admin(app, operational_engine.sync_engine if hasattr(operational_engine, 'sync_engine') else None) # Handle sync_engine for sqladmin if needed

# Add Admin Views (Skipping complex sync/async mismatch for sqladmin in this simplified refactor step)
# In production, we'd ensure sqladmin works with our async engine

@app.get("/")
def read_root():
    return {"message": f"{settings.PROJECT_NAME} V2 is Running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
