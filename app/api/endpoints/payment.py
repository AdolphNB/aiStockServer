"""
Payment API Endpoints
Handles subscription payments via WeChat Pay
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import secrets
import logging
import uuid

from app.core.database import get_db
from app.core.config import settings
from app.models.models import PaymentOrder, Subscription
from app.services.wechat_pay import get_wechat_pay_service

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Schemas ---

class PaymentOrderCreate(BaseModel):
    machine_id: str
    plan_type: str  # "1m", "3m", "6m", "12m"

class PaymentOrderResponse(BaseModel):
    order_no: str
    amount: float
    qr_code_url: str
    expires_at: str
    plan_type: str

class PaymentStatusResponse(BaseModel):
    order_no: str
    status: str  # "pending", "paid", "expired", "cancelled"
    token: Optional[str] = None
    subscription_end_date: Optional[str] = None

# --- Endpoints ---

@router.post("/create-order", response_model=PaymentOrderResponse)
def create_payment_order(
    order_create: PaymentOrderCreate,
    db: Session = Depends(get_db)
):
    """
    Create a payment order and return QR code URL for WeChat Pay
    
    Flow:
    1. Validate plan type
    2. Generate unique order number
    3. Create order in database
    4. Call WeChat Pay API to get QR code URL
    5. Return QR code URL to client
    """
    # Validate plan type
    if order_create.plan_type not in settings.PLAN_PRICES:
        raise HTTPException(status_code=400, detail="Invalid plan type")
    
    # Get price for the plan
    amount = settings.PLAN_PRICES[order_create.plan_type]
    
    # Generate unique order number
    order_no = f"ORDER_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8].upper()}"
    
    # Create order in database
    new_order = PaymentOrder(
        order_no=order_no,
        machine_id=order_create.machine_id,
        plan_type=order_create.plan_type,
        amount=amount,
        payment_method="wechat",
        payment_status="pending",
        expires_at=datetime.now() + timedelta(hours=2)  # Order expires in 2 hours
    )
    
    try:
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating order in database: {e}")
        raise HTTPException(status_code=500, detail="Failed to create order")
    
    # Get WeChat Pay service
    wechat_service = get_wechat_pay_service()
    
    # Create WeChat Pay Native order
    plan_names = {
        "1m": "AIStock订阅 - 1个月",
        "3m": "AIStock订阅 - 3个月",
        "6m": "AIStock订阅 - 6个月",
        "12m": "AIStock订阅 - 12个月"
    }
    
    wechat_result = wechat_service.create_native_order(
        order_no=order_no,
        total_fee=amount,
        description=plan_names.get(order_create.plan_type, "AIStock订阅"),
        machine_id=order_create.machine_id
    )
    
    if not wechat_result:
        # Failed to create WeChat order
        new_order.payment_status = "cancelled"
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to create WeChat Pay order")
    
    # Update order with WeChat Pay info
    new_order.wechat_code_url = wechat_result['code_url']
    new_order.wechat_prepay_id = wechat_result['prepay_id']
    db.commit()
    
    logger.info(f"Payment order created: {order_no}, amount: {amount}, machine: {order_create.machine_id}")
    
    return {
        "order_no": order_no,
        "amount": amount,
        "qr_code_url": wechat_result['code_url'],
        "expires_at": new_order.expires_at.isoformat(),
        "plan_type": order_create.plan_type
    }


@router.get("/order-status/{order_no}", response_model=PaymentStatusResponse)
def check_payment_status(
    order_no: str,
    db: Session = Depends(get_db)
):
    """
    Check payment order status
    Client should poll this endpoint after displaying QR code
    """
    order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order has expired
    if order.payment_status == "pending" and order.expires_at < datetime.now():
        order.payment_status = "expired"
        db.commit()
    
    # If order is already paid, return subscription info
    if order.payment_status == "paid" and order.subscription:
        return {
            "order_no": order_no,
            "status": order.payment_status,
            "token": order.subscription.token,
            "subscription_end_date": order.subscription.end_date.isoformat()
        }
    
    # For pending orders, query WeChat Pay to check latest status
    if order.payment_status == "pending":
        wechat_service = get_wechat_pay_service()
        wechat_status = wechat_service.query_order(order_no)
        
        if wechat_status and wechat_status.get('trade_state') == 'SUCCESS':
            # Payment successful, activate subscription
            _activate_subscription(order, db, wechat_status.get('transaction_id'))
            
            return {
                "order_no": order_no,
                "status": "paid",
                "token": order.subscription.token,
                "subscription_end_date": order.subscription.end_date.isoformat()
            }
    
    return {
        "order_no": order_no,
        "status": order.payment_status,
        "token": None,
        "subscription_end_date": None
    }


@router.post("/wechat/notify")
async def wechat_pay_notify(request: Request, db: Session = Depends(get_db)):
    """
    WeChat Pay callback notification endpoint
    This is called by WeChat servers after successful payment
    """
    try:
        # Get raw XML body
        body = await request.body()
        body_str = body.decode('utf-8')
        
        logger.info(f"Received WeChat Pay notification: {body_str[:200]}")
        
        # Parse XML to dict (simplified, should use proper XML parser)
        # For production, use the wechat_pay service to parse XML
        from xml.etree import ElementTree as ET
        root = ET.fromstring(body_str)
        notify_data = {child.tag: child.text for child in root}
        
        # Verify signature
        wechat_service = get_wechat_pay_service()
        if not wechat_service.verify_notify(notify_data):
            logger.error("WeChat Pay notification signature verification failed")
            return Response(
                content=wechat_service.generate_notify_response(False, "Signature verification failed"),
                media_type="application/xml"
            )
        
        # Check if payment is successful
        if notify_data.get('result_code') != 'SUCCESS':
            logger.warning(f"WeChat Pay notification: payment not successful - {notify_data}")
            return Response(
                content=wechat_service.generate_notify_response(True, "OK"),
                media_type="application/xml"
            )
        
        # Get order number
        order_no = notify_data.get('out_trade_no')
        transaction_id = notify_data.get('transaction_id')
        
        if not order_no:
            logger.error("WeChat Pay notification: missing order number")
            return Response(
                content=wechat_service.generate_notify_response(False, "Missing order number"),
                media_type="application/xml"
            )
        
        # Find order in database
        order = db.query(PaymentOrder).filter(PaymentOrder.order_no == order_no).first()
        
        if not order:
            logger.error(f"WeChat Pay notification: order not found - {order_no}")
            return Response(
                content=wechat_service.generate_notify_response(False, "Order not found"),
                media_type="application/xml"
            )
        
        # Check if already processed
        if order.payment_status == "paid":
            logger.info(f"WeChat Pay notification: order already processed - {order_no}")
            return Response(
                content=wechat_service.generate_notify_response(True, "OK"),
                media_type="application/xml"
            )
        
        # Activate subscription
        _activate_subscription(order, db, transaction_id)
        
        logger.info(f"WeChat Pay notification processed successfully: {order_no}")
        
        return Response(
            content=wechat_service.generate_notify_response(True, "OK"),
            media_type="application/xml"
        )
        
    except Exception as e:
        logger.error(f"Error processing WeChat Pay notification: {e}")
        wechat_service = get_wechat_pay_service()
        return Response(
            content=wechat_service.generate_notify_response(False, str(e)),
            media_type="application/xml"
        )


def _activate_subscription(order: PaymentOrder, db: Session, transaction_id: Optional[str] = None):
    """
    Internal function to activate subscription after successful payment
    """
    try:
        # Calculate subscription duration
        days_map = {
            "1m": 30,
            "3m": 90,
            "6m": 180,
            "12m": 365
        }
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        end_date = datetime.now() + timedelta(days=days_map[order.plan_type])
        
        # Create subscription
        new_subscription = Subscription(
            machine_id=order.machine_id,
            token=token,
            plan_type=order.plan_type,
            end_date=end_date,
            is_active=True
        )
        
        db.add(new_subscription)
        db.flush()  # Get subscription ID
        
        # Update order
        order.payment_status = "paid"
        order.paid_at = datetime.now()
        order.wechat_transaction_id = transaction_id
        order.subscription_id = new_subscription.id
        
        db.commit()
        
        logger.info(f"Subscription activated: token={token}, order={order.order_no}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error activating subscription: {e}")
        raise
