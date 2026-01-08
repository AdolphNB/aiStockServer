"""
WeChat Pay Service Module
Implements WeChat Native Pay (扫码支付) for subscription payments
"""
import hashlib
import time
import uuid
import logging
import requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)

class WeChatPayService:
    """WeChat Pay Native (v2) implementation"""
    
    # WeChat Pay API endpoints
    UNIFIED_ORDER_URL = "https://api.mch.weixin.qq.com/pay/unifiedorder"
    ORDER_QUERY_URL = "https://api.mch.weixin.qq.com/pay/orderquery"
    
    def __init__(self):
        self.appid = settings.WECHAT_APPID
        self.mch_id = settings.WECHAT_MCHID
        self.api_key = settings.WECHAT_API_KEY
        self.notify_url = f"{settings.SERVER_URL}/api/v1/payment/wechat/notify"
    
    def _generate_sign(self, params: Dict) -> str:
        """
        Generate MD5 signature for WeChat Pay API
        Args:
            params: Dictionary of parameters (excluding 'sign')
        Returns:
            MD5 signature string
        """
        # Sort parameters by key and concatenate
        sorted_params = sorted(params.items())
        string_params = "&".join([f"{k}={v}" for k, v in sorted_params if v])
        # Append API key
        string_sign_temp = f"{string_params}&key={self.api_key}"
        # MD5 hash and uppercase
        sign = hashlib.md5(string_sign_temp.encode('utf-8')).hexdigest().upper()
        return sign
    
    def _dict_to_xml(self, data: Dict) -> str:
        """Convert dictionary to XML format"""
        xml_parts = ['<xml>']
        for key, value in data.items():
            xml_parts.append(f'<{key}><![CDATA[{value}]]></{key}>')
        xml_parts.append('</xml>')
        return ''.join(xml_parts)
    
    def _xml_to_dict(self, xml_str: str) -> Dict:
        """Convert XML string to dictionary"""
        root = ET.fromstring(xml_str)
        return {child.tag: child.text for child in root}
    
    def create_native_order(
        self,
        order_no: str,
        total_fee: float,
        description: str,
        machine_id: str
    ) -> Optional[Dict]:
        """
        Create a WeChat Native Pay order and get QR code URL
        
        Args:
            order_no: Unique order number
            total_fee: Payment amount in CNY (will be converted to fen)
            description: Product description
            machine_id: Client machine ID
        
        Returns:
            Dictionary with 'code_url' and 'prepay_id' if successful, None otherwise
        """
        try:
            # Convert yuan to fen (WeChat uses fen as smallest unit)
            total_fee_fen = int(total_fee * 100)
            
            # Prepare parameters
            params = {
                'appid': self.appid,
                'mch_id': self.mch_id,
                'nonce_str': uuid.uuid4().hex,
                'body': description,
                'out_trade_no': order_no,
                'total_fee': str(total_fee_fen),
                'spbill_create_ip': '127.0.0.1',  # Should be server IP
                'notify_url': self.notify_url,
                'trade_type': 'NATIVE',
                'product_id': order_no,
                'attach': machine_id  # Store machine_id in attach field
            }
            
            # Generate signature
            params['sign'] = self._generate_sign(params)
            
            # Convert to XML
            xml_data = self._dict_to_xml(params)
            
            logger.info(f"Creating WeChat Pay order: {order_no}")
            
            # Send request to WeChat
            response = requests.post(
                self.UNIFIED_ORDER_URL,
                data=xml_data.encode('utf-8'),
                headers={'Content-Type': 'application/xml'},
                timeout=10
            )
            
            # Parse response
            result = self._xml_to_dict(response.text)
            
            if result.get('return_code') == 'SUCCESS' and result.get('result_code') == 'SUCCESS':
                logger.info(f"WeChat Pay order created successfully: {order_no}")
                return {
                    'code_url': result.get('code_url'),
                    'prepay_id': result.get('prepay_id')
                }
            else:
                logger.error(f"WeChat Pay order creation failed: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating WeChat Pay order: {e}")
            return None
    
    def query_order(self, order_no: str) -> Optional[Dict]:
        """
        Query order status from WeChat Pay
        
        Args:
            order_no: Order number
        
        Returns:
            Dictionary with order details if successful
        """
        try:
            params = {
                'appid': self.appid,
                'mch_id': self.mch_id,
                'out_trade_no': order_no,
                'nonce_str': uuid.uuid4().hex
            }
            
            # Generate signature
            params['sign'] = self._generate_sign(params)
            
            # Convert to XML
            xml_data = self._dict_to_xml(params)
            
            # Send request
            response = requests.post(
                self.ORDER_QUERY_URL,
                data=xml_data.encode('utf-8'),
                headers={'Content-Type': 'application/xml'},
                timeout=10
            )
            
            # Parse response
            result = self._xml_to_dict(response.text)
            
            if result.get('return_code') == 'SUCCESS':
                return result
            else:
                logger.error(f"WeChat Pay query failed: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying WeChat Pay order: {e}")
            return None
    
    def verify_notify(self, notify_data: Dict) -> bool:
        """
        Verify WeChat Pay callback notification
        
        Args:
            notify_data: Dictionary of notification parameters
        
        Returns:
            True if verification succeeds
        """
        try:
            # Extract sign from notification
            received_sign = notify_data.get('sign', '')
            
            # Remove sign from data
            verify_data = {k: v for k, v in notify_data.items() if k != 'sign' and v}
            
            # Calculate expected sign
            expected_sign = self._generate_sign(verify_data)
            
            return received_sign == expected_sign
            
        except Exception as e:
            logger.error(f"Error verifying WeChat Pay notification: {e}")
            return False
    
    def generate_notify_response(self, success: bool = True, msg: str = "OK") -> str:
        """
        Generate XML response for WeChat Pay callback
        
        Args:
            success: Whether the processing was successful
            msg: Return message
        
        Returns:
            XML response string
        """
        return_code = "SUCCESS" if success else "FAIL"
        return f"""<xml>
    <return_code><![CDATA[{return_code}]]></return_code>
    <return_msg><![CDATA[{msg}]]></return_msg>
</xml>"""


# Mock WeChat Pay Service for testing without real WeChat credentials
class MockWeChatPayService(WeChatPayService):
    """Mock implementation for testing purposes"""
    
    def create_native_order(
        self,
        order_no: str,
        total_fee: float,
        description: str,
        machine_id: str
    ) -> Optional[Dict]:
        """Return a mock QR code URL"""
        logger.info(f"[MOCK] Creating WeChat Pay order: {order_no}, amount: {total_fee}")
        
        # Generate a mock QR code URL
        mock_code_url = f"weixin://wxpay/bizpayurl?pr=mock{order_no[:8]}"
        
        return {
            'code_url': mock_code_url,
            'prepay_id': f"mock_prepay_{uuid.uuid4().hex[:16]}"
        }
    
    def query_order(self, order_no: str) -> Optional[Dict]:
        """Return mock order status (always pending for testing)"""
        logger.info(f"[MOCK] Querying order: {order_no}")
        
        return {
            'return_code': 'SUCCESS',
            'result_code': 'SUCCESS',
            'trade_state': 'NOTPAY',  # Can be: NOTPAY, SUCCESS, REFUND, CLOSED, etc.
            'out_trade_no': order_no
        }
    
    def verify_notify(self, notify_data: Dict) -> bool:
        """Mock verification always succeeds"""
        logger.info(f"[MOCK] Verifying notification for order: {notify_data.get('out_trade_no')}")
        return True


# Factory function to get the appropriate service
def get_wechat_pay_service() -> WeChatPayService:
    """
    Get WeChat Pay service instance
    Returns mock service if credentials are not configured
    """
    if settings.WECHAT_APPID and settings.WECHAT_MCHID and settings.WECHAT_API_KEY:
        logger.info("Using real WeChat Pay service")
        return WeChatPayService()
    else:
        logger.warning("WeChat Pay credentials not configured, using mock service")
        return MockWeChatPayService()
