from sqlalchemy import Boolean, Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(String, index=True, nullable=True) # ID of the PC Client
    token = Column(String, unique=True, index=True)
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True))
    plan_type = Column(String) # "1m", "3m", "6m", "12m"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship with payment orders
    orders = relationship("PaymentOrder", back_populates="subscription")

class PaymentOrder(Base):
    __tablename__ = "payment_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String, unique=True, index=True)  # Internal order number
    machine_id = Column(String, index=True)
    plan_type = Column(String)  # "1m", "3m", "6m", "12m"
    amount = Column(Float)  # Payment amount in CNY
    payment_method = Column(String, default="wechat")  # "wechat", "alipay"
    payment_status = Column(String, default="pending")  # "pending", "paid", "expired", "cancelled"
    
    # WeChat Pay specific fields
    wechat_prepay_id = Column(String, nullable=True)  # WeChat prepay_id
    wechat_code_url = Column(String, nullable=True)  # QR code URL for Native Pay
    wechat_transaction_id = Column(String, nullable=True)  # WeChat transaction ID after payment
    
    # Subscription link
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    subscription = relationship("Subscription", back_populates="orders")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True))  # Order expiration time (typically 2 hours)

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
