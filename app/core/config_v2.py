from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "AIStock Remote Server"
    API_V1_STR: str = "/api/v1"
    
    # Base Directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # Data & Code Separation (As requested)
    # All data will be stored in the root /data directory
    DATA_DIR: Path = BASE_DIR / "data"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SERVER_URL: str = "http://www.mcptools.xin"
    
    # Security
    SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_SECRET_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # Database (Operational) - SQLite or Postgres
    # For SQLite, it will be saved in data directory
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DATA_DIR}/aistock.db"
    
    # Realtime Market Data DB (WAL Mode)
    # Dedicated DB for High-Frequency updates
    REALTIME_DB_PATH: Path = DATA_DIR / "realtime_kline.db"
    REALTIME_DB_URL: str = f"sqlite+aiosqlite:///{REALTIME_DB_PATH}"
    
    # Shared Cache (Legacy support if needed)
    SHARED_CACHE_DIR: Path = DATA_DIR / "shared_cache"
    
    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    
    # WeChat Pay
    WECHAT_APPID: str = ""
    WECHAT_MCHID: str = ""
    WECHAT_API_KEY: str = ""
    WECHAT_API_V3_KEY: str = ""
    WECHAT_CERT_SERIAL_NO: str = ""
    WECHAT_PRIVATE_KEY_PATH: str = ""
    
    # Pricing
    PLAN_PRICES: dict = {
        "1m": 29.90,
        "3m": 79.90,
        "6m": 149.90,
        "12m": 269.90
    }
    
    # Interval Settings
    REALTIME_FETCH_INTERVAL: int = 60
    
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.SHARED_CACHE_DIR, exist_ok=True)
