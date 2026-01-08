"""
AIStock PC Client Example
演示如何从PC客户端调用AIStock服务器API

功能：
1. 创建支付订单并获取二维码
2. 轮询查询支付状态
3. 获取token后访问股票数据
"""

import requests
import time
import qrcode  # pip install qrcode[pil]
from typing import Optional

class AIStockClient:
    """AIStock服务器客户端"""
    
    def __init__(self, server_url: str = "https://www.mcptools.xin"):
        self.server_url = server_url
        self.api_base = f"{server_url}/api/v1"
        self.token: Optional[str] = None
    
    def create_payment_order(self, machine_id: str, plan_type: str) -> dict:
        """
        创建支付订单
        
        Args:
            machine_id: 机器ID（可以使用MAC地址或其他唯一标识）
            plan_type: 套餐类型 ("1m", "3m", "6m", "12m")
        
        Returns:
            订单信息，包含二维码URL
        """
        url = f"{self.api_base}/payment/create-order"
        payload = {
            "machine_id": machine_id,
            "plan_type": plan_type
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        return response.json()
    
    def check_payment_status(self, order_no: str) -> dict:
        """
        查询支付状态
        
        Args:
            order_no: 订单号
        
        Returns:
            支付状态信息
        """
        url = f"{self.api_base}/payment/order-status/{order_no}"
        response = requests.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def wait_for_payment(self, order_no: str, timeout: int = 300, interval: int = 3) -> Optional[str]:
        """
        等待支付完成（轮询）
        
        Args:
            order_no: 订单号
            timeout: 超时时间（秒）
            interval: 轮询间隔（秒）
        
        Returns:
            支付成功返回token，超时或失败返回None
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.check_payment_status(order_no)
            
            if status['status'] == 'paid':
                self.token = status.get('token')
                print(f"✅ 支付成功！Token: {self.token}")
                return self.token
            elif status['status'] == 'expired':
                print("❌ 订单已过期")
                return None
            elif status['status'] == 'cancelled':
                print("❌ 订单已取消")
                return None
            
            # 等待后继续轮询
            print(f"⏳ 等待支付中... ({int(time.time() - start_time)}秒)")
            time.sleep(interval)
        
        print("⏰ 支付超时")
        return None
    
    def get_market_activity(self) -> dict:
        """
        获取市场活跃度数据（赚钱效应）
        需要有效的token
        
        Returns:
            市场活跃度数据
        """
        if not self.token:
            raise ValueError("需要先订阅并获取token")
        
        url = f"{self.api_base}/data/market-activity"
        params = {"token": self.token}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_sse_summary(self) -> dict:
        """
        获取上交所汇总数据（公开接口，不需要token）
        
        Returns:
            上交所汇总数据
        """
        url = f"{self.server_url}/sse-summary"
        response = requests.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def display_qr_code(self, code_url: str):
        """
        显示二维码（在终端或GUI）
        
        Args:
            code_url: 微信支付二维码URL
        """
        # 生成二维码图片
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(code_url)
        qr.make(fit=True)
        
        # 在终端显示（文本版）
        qr.print_ascii()
        
        # 也可以生成图片文件
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("payment_qrcode.png")
        print("\n💾 二维码已保存为: payment_qrcode.png")
        print("📱 请使用微信扫描二维码完成支付")


def get_machine_id() -> str:
    """
    获取机器唯一标识
    实际应用中可以使用MAC地址、硬件ID等
    """
    import uuid
    mac = uuid.getnode()
    return str(mac)


def main():
    """主函数 - 演示完整流程"""
    
    # 初始化客户端
    client = AIStockClient("https://www.mcptools.xin")
    
    # 获取机器ID
    machine_id = get_machine_id()
    print(f"🖥️  机器ID: {machine_id}")
    
    # 选择订阅套餐
    print("\n📋 可选套餐：")
    print("  1m  - 1个月   (¥29.90)")
    print("  3m  - 3个月   (¥79.90)")
    print("  6m  - 6个月   (¥149.90)")
    print("  12m - 12个月  (¥269.90)")
    
    plan_type = input("\n请选择套餐 (1m/3m/6m/12m): ").strip()
    
    if plan_type not in ["1m", "3m", "6m", "12m"]:
        print("❌ 无效的套餐类型")
        return
    
    # 创建支付订单
    print(f"\n🛒 创建支付订单...")
    try:
        order = client.create_payment_order(machine_id, plan_type)
        print(f"✅ 订单创建成功！")
        print(f"   订单号: {order['order_no']}")
        print(f"   金额: ¥{order['amount']}")
        print(f"   过期时间: {order['expires_at']}")
        
        # 显示二维码
        print("\n🔲 生成支付二维码...")
        client.display_qr_code(order['qr_code_url'])
        
        # 等待支付完成
        print("\n⏳ 等待支付完成...")
        token = client.wait_for_payment(order['order_no'], timeout=300, interval=3)
        
        if token:
            print(f"\n🎉 订阅成功！您的Token: {token}")
            print("💾 请妥善保存此Token，用于访问数据")
            
            # 测试获取数据
            print("\n📊 测试获取市场数据...")
            market_data = client.get_market_activity()
            print(f"✅ 数据获取成功！")
            print(f"   更新时间: {market_data['timestamp']}")
            print(f"   数据条数: {len(market_data['data']) if market_data['data'] else 0}")
            
            # 显示部分数据
            if market_data['data']:
                print("\n📈 市场活跃度数据样例：")
                for item in market_data['data'][:3]:  # 显示前3条
                    print(f"   {item}")
        else:
            print("\n❌ 订阅失败")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
    except Exception as e:
        print(f"❌ 错误: {e}")


def demo_with_existing_token():
    """
    如果已经有token，直接使用token获取数据
    """
    client = AIStockClient("https://www.mcptools.xin")
    
    # 使用已有的token
    existing_token = input("请输入您的Token: ").strip()
    client.token = existing_token
    
    try:
        # 获取市场活跃度数据
        print("\n📊 获取市场活跃度数据...")
        market_data = client.get_market_activity()
        print(f"✅ 数据获取成功！")
        print(f"   更新时间: {market_data['timestamp']}")
        
        if market_data['data']:
            print(f"\n📈 共 {len(market_data['data'])} 条数据")
            for item in market_data['data'][:5]:
                print(f"   {item}")
        
        # 获取上交所汇总数据（无需token）
        print("\n📊 获取上交所汇总数据...")
        sse_data = client.get_sse_summary()
        print(f"✅ 数据获取成功！")
        print(f"   更新时间: {sse_data['timestamp']}")
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("❌ Token无效")
        elif e.response.status_code == 403:
            print("❌ 订阅已过期或未激活")
        else:
            print(f"❌ 请求失败: {e}")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("   AIStock 客户端示例")
    print("=" * 60)
    
    print("\n请选择操作：")
    print("  1. 新订阅（创建支付订单）")
    print("  2. 使用已有Token获取数据")
    
    choice = input("\n请选择 (1/2): ").strip()
    
    if choice == "1":
        main()
    elif choice == "2":
        demo_with_existing_token()
    else:
        print("❌ 无效的选择")
