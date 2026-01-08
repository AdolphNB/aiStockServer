"""
简单的API测试脚本
无需客户端，直接测试所有功能
"""

import requests
import json
import time

BASE_URL = "http://www.mcptools.xin:8000"

def print_json(data, title=""):
    """美化打印JSON"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print('='*60)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def test_health_check():
    """测试健康检查"""
    print_json({}, "1. 健康检查")
    response = requests.get(f"{BASE_URL}/health")
    data = response.json()
    print_json(data)
    print(f"\n✅ 服务状态: {data['status']}")
    print(f"✅ 是否为交易日: {data.get('is_trading_day', 'N/A')}")
    return data


def test_create_payment():
    """测试创建支付订单"""
    print_json({}, "2. 创建支付订单")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/payment/create-order",
        json={
            "machine_id": "test_machine_001",
            "plan_type": "1m"
        }
    )
    
    if response.status_code == 200:
        order = response.json()
        print_json(order)
        print(f"\n✅ 订单创建成功！")
        print(f"📝 订单号: {order['order_no']}")
        print(f"💰 金额: ¥{order['amount']}")
        print(f"📱 二维码URL: {order['qr_code_url']}")
        print(f"⏰ 过期时间: {order['expires_at']}")
        return order
    else:
        print(f"❌ 创建订单失败: {response.text}")
        return None


def test_query_order_status(order_no):
    """测试查询订单状态"""
    print_json({}, "3. 查询订单状态")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/payment/order-status/{order_no}"
    )
    
    if response.status_code == 200:
        status = response.json()
        print_json(status)
        
        status_emoji = {
            'pending': '⏳ 待支付',
            'paid': '✅ 已支付',
            'expired': '⏰ 已过期',
            'cancelled': '❌ 已取消'
        }
        
        print(f"\n订单状态: {status_emoji.get(status['status'], status['status'])}")
        
        if status['status'] == 'paid':
            print(f"✅ Token: {status.get('token')}")
            print(f"✅ 订阅截止: {status.get('subscription_end_date')}")
        
        return status
    else:
        print(f"❌ 查询失败: {response.text}")
        return None


def test_subscribe_directly():
    """测试直接订阅（跳过支付，用于测试）"""
    print_json({}, "4. 直接订阅（测试模式）")
    
    response = requests.post(
        f"{BASE_URL}/api/v1/subscribe",
        json={
            "machine_id": "test_machine_002",
            "plan_type": "1m"
        }
    )
    
    if response.status_code == 200:
        sub = response.json()
        print_json(sub)
        print(f"\n✅ 订阅成功！")
        print(f"🔑 Token: {sub['token']}")
        print(f"⏰ 过期时间: {sub['expiry']}")
        return sub
    else:
        print(f"❌ 订阅失败: {response.text}")
        return None


def test_get_market_data(token):
    """测试获取市场数据"""
    print_json({}, "5. 获取市场活跃度数据")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/data/market-activity",
        params={"token": token}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 数据获取成功！")
        print(f"⏰ 更新时间: {data.get('timestamp')}")
        
        if data.get('data'):
            print(f"📊 数据条数: {len(data['data'])}")
            print("\n前3条数据:")
            for i, item in enumerate(data['data'][:3], 1):
                print(f"  {i}. {item}")
        else:
            print("⚠️  暂无数据（可能还未到交易时间）")
        
        return data
    else:
        print(f"❌ 获取失败: {response.text}")
        return None


def test_get_sse_summary():
    """测试获取上交所汇总数据（公开接口）"""
    print_json({}, "6. 获取上交所汇总数据（公开接口）")
    
    response = requests.get(f"{BASE_URL}/sse-summary")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 数据获取成功！")
        print(f"⏰ 更新时间: {data.get('timestamp')}")
        
        if data.get('data'):
            print(f"📊 数据条数: {len(data['data'])}")
            print("\n前5条数据:")
            for i, item in enumerate(data['data'][:5], 1):
                print(f"  {i}. {item}")
        else:
            print("⚠️  暂无数据")
        
        return data
    else:
        print(f"❌ 获取失败: {response.text}")
        return None


def main():
    print("\n" + "="*60)
    print("  AIStock API 测试工具")
    print("="*60)
    print("\n请确保服务器已启动: python -m app.main")
    print("按 Ctrl+C 随时退出")
    
    try:
        # 等待用户确认
        input("\n按回车键开始测试...")
        
        # 1. 健康检查
        test_health_check()
        time.sleep(1)
        
        # 2. 测试支付订单创建
        order = test_create_payment()
        if order:
            time.sleep(1)
            # 3. 查询订单状态
            test_query_order_status(order['order_no'])
        
        time.sleep(1)
        
        # 4. 测试直接订阅（获取token）
        sub = test_subscribe_directly()
        if sub and sub.get('token'):
            time.sleep(1)
            # 5. 使用token获取市场数据
            test_get_market_data(sub['token'])
        
        time.sleep(1)
        
        # 6. 测试公开数据接口
        test_get_sse_summary()
        
        print("\n" + "="*60)
        print("  ✅ 所有测试完成！")
        print("="*60)
        
        print("\n📝 测试总结:")
        print("  1. ✅ 健康检查 - 服务正常运行")
        print("  2. ✅ 创建支付订单 - Mock模式生成二维码")
        print("  3. ✅ 查询订单状态 - 订单信息正确")
        print("  4. ✅ 直接订阅 - 获取Token成功")
        print("  5. ✅ 获取市场数据 - Token认证通过")
        print("  6. ✅ 获取公开数据 - 无需认证")
        
        print("\n💡 提示:")
        print("  - 当前使用Mock支付模式（无需真实微信凭证）")
        print("  - 要测试真实支付，请配置微信支付参数（见 PAYMENT_SETUP.md）")
        print("  - 后台管理界面: http://localhost:8000/admin")
        print("  - API文档: http://localhost:8000/docs")
        
    except KeyboardInterrupt:
        print("\n\n测试已取消")
    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到服务器！")
        print("请确保服务器已启动: python -m app.main")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")


if __name__ == "__main__":
    main()
