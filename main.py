from fastapi import FastAPI
from sqladmin import Admin, ModelView
import logging

from config import settings
from database import engine, Base
from models import Subscription, AdminUser
from routers import client
from scheduler import start_scheduler

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

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

@app.on_event("startup")
async def startup_event():
    start_scheduler()
    logger.info("Application starting up...")

@app.get("/")
def read_root():
    return {"message": "AIStock Remote Server is Running"}
