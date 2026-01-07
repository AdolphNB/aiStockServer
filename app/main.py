from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqladmin import Admin, ModelView
import logging

from app.core.config import settings
from app.core.database import engine, Base
from app.models.models import Subscription, AdminUser
from app.api.endpoints import client
from app.services.scheduler import start_scheduler

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    logger.info("Application starting up...")
    yield

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Include Routers
app.include_router(client.router, prefix=settings.API_V1_STR, tags=["Client"])

# Admin Interface
admin = Admin(app, engine)

class SubscriptionAdmin(ModelView, model=Subscription):
    column_list = [Subscription.id, Subscription.machine_id, Subscription.plan_type, Subscription.is_active, Subscription.end_date]
    form_columns = [Subscription.machine_id, Subscription.token, Subscription.plan_type, Subscription.is_active, Subscription.end_date] 

class UserAdmin(ModelView, model=AdminUser):
    column_list = [AdminUser.id, AdminUser.username]

admin.add_view(SubscriptionAdmin)
admin.add_view(UserAdmin)

@app.get("/")
def read_root():
    return {"message": "AIStock Remote Server is Running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
