import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AIStock Remote Server"
    API_V1_STR: str = "/api/v1"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))  # Default to port 8000, can be overridden by PORT env var
    SERVER_URL: str = os.getenv("SERVER_URL", "http://www.mcptools.xin")  # Public server URL
    
    # Security
    SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_SECRET_KEY"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # Database
    DATABASE_URL: str = "sqlite:///./aistock.db"
    
    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    
    # WeChat Pay Configuration
    WECHAT_APPID: str = os.getenv("WECHAT_APPID", "")  # WeChat App ID
    WECHAT_MCHID: str = os.getenv("WECHAT_MCHID", "")  # Merchant ID
    WECHAT_API_KEY: str = os.getenv("WECHAT_API_KEY", "")  # API Key (v2)
    WECHAT_API_V3_KEY: str = os.getenv("WECHAT_API_V3_KEY", "")  # API v3 Key
    WECHAT_CERT_SERIAL_NO: str = os.getenv("WECHAT_CERT_SERIAL_NO", "")  # Certificate serial number
    WECHAT_PRIVATE_KEY_PATH: str = os.getenv("WECHAT_PRIVATE_KEY_PATH", "")  # Path to private key file
    
    # Payment settings
    PLAN_PRICES: dict = {
        "1m": 29.90,
        "3m": 79.90,
        "6m": 149.90,
        "12m": 269.90
    }
    
    # Stock Data Settings
    DATA_DIR: str = "data"  # Directory for data storage
    SHARED_CACHE_DIR: str = "shared_cache"  # Directory for high-performance shared cache
    KLINE_DAYS: int = 90  # Number of days to keep for daily K-line data
    REALTIME_FETCH_INTERVAL: int = 60  # Seconds between realtime data fetches
    FUND_FLOW_FETCH_INTERVAL: int = 300  # Seconds between fund flow fetches (5 minutes)
    STOCK_CHANGES_FETCH_INTERVAL: int = 300  # Seconds between stock changes fetches (5 minutes)
    
    class Config:
        case_sensitive = True

settings = Settings()
