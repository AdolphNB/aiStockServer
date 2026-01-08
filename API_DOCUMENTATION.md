# AIStock Server API 文档

## 概述

AIStock Server 提供RESTful API接口，用于：
- 订阅管理和支付
- 获取股票市场数据
- 后台管理

**Base URL**: `https://www.mcptools.xin`  
**API Version**: v1  
**API Prefix**: `/api/v1`

## 认证方式

大部分API需要Token认证。通过订阅获取Token后，在请求中携带token参数。

```
GET /api/v1/data/market-activity?token=YOUR_TOKEN
```

## API 端点

### 1. 健康检查

#### GET /health

检查服务器状态和数据更新情况。

**请求**

```bash
curl https://www.mcptools.xin/health
```

**响应**

```json
{
  "status": "running",
  "port": 8000,
  "has_market_activity": true,
  "market_activity_last_updated": "2026-01-08T14:23:45.123456",
  "has_sse_summary": true,
  "sse_summary_last_updated": "2026-01-08T14:23:45.123456",
  "is_trading_day": true,
  "trading_calendar_cache": {
    "total_trading_days": 245,
    "last_update": "2026-01-08T00:00:00",
    "cache_valid": true
  }
}
```

---

### 2. 支付相关接口

#### POST /api/v1/payment/create-order

创建支付订单，获取微信支付二维码。

**请求**

```bash
curl -X POST https://www.mcptools.xin/api/v1/payment/create-order \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "your_machine_id",
    "plan_type": "1m"
  }'
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| machine_id | string | 是 | 机器唯一标识（MAC地址等） |
| plan_type | string | 是 | 套餐类型：1m/3m/6m/12m |

**响应**

```json
{
  "order_no": "ORDER_20260108143045_A1B2C3D4",
  "amount": 29.9,
  "qr_code_url": "weixin://wxpay/bizpayurl?pr=xxx",
  "expires_at": "2026-01-08T16:30:45.123456",
  "plan_type": "1m"
}
```

**错误响应**

```json
{
  "detail": "Invalid plan type"
}
```

---

#### GET /api/v1/payment/order-status/{order_no}

查询订单支付状态。客户端应定期轮询此接口检查支付是否完成。

**请求**

```bash
curl https://www.mcptools.xin/api/v1/payment/order-status/ORDER_20260108143045_A1B2C3D4
```

**响应 - 待支付**

```json
{
  "order_no": "ORDER_20260108143045_A1B2C3D4",
  "status": "pending",
  "token": null,
  "subscription_end_date": null
}
```

**响应 - 已支付**

```json
{
  "order_no": "ORDER_20260108143045_A1B2C3D4",
  "status": "paid",
  "token": "xJd8fK2mL9pQ4vN7wR1sA6tB3uY5cZ0e",
  "subscription_end_date": "2026-02-08T14:30:45.123456"
}
```

**订单状态**

| 状态 | 说明 |
|------|------|
| pending | 待支付 |
| paid | 已支付 |
| expired | 已过期 |
| cancelled | 已取消 |

---

#### POST /api/v1/payment/wechat/notify

微信支付回调通知接口（由微信服务器调用，客户端无需调用）。

---

### 3. 数据获取接口

#### GET /api/v1/data/market-activity

获取市场活跃度数据（赚钱效应分析）。

**需要认证：是**

**请求**

```bash
curl "https://www.mcptools.xin/api/v1/data/market-activity?token=YOUR_TOKEN"
```

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| token | string | 是 | 订阅token |

**响应**

```json
{
  "timestamp": "2026-01-08T14:23:45.123456",
  "data": [
    {
      "日期": "2026-01-08",
      "上涨家数": 2456,
      "下跌家数": 1234,
      "涨停家数": 45,
      "跌停家数": 12,
      "涨幅中位数": 0.85,
      "涨跌比": 1.99
    },
    ...
  ]
}
```

**错误响应**

```json
// 401 - Token无效
{
  "detail": "Invalid token"
}

// 403 - 订阅未激活
{
  "detail": "Subscription inactive"
}

// 403 - 订阅已过期
{
  "detail": "Subscription expired"
}
```

---

#### GET /sse-summary

获取上交所汇总数据（公开接口）。

**需要认证：否**

**请求**

```bash
curl https://www.mcptools.xin/sse-summary
```

**响应**

```json
{
  "timestamp": "2026-01-08T14:23:45.123456",
  "data": [
    {
      "项目": "流通市值",
      "股票": "479,876.32",
      "单位": "亿元"
    },
    {
      "项目": "总市值",
      "股票": "589,234.56",
      "单位": "亿元"
    },
    ...
  ]
}
```

---

#### GET /api/v1/data/sse-summary

获取上交所汇总数据（同上，API版本）。

**需要认证：否**

---

### 4. 订阅接口（旧版，已弃用）

#### POST /api/v1/subscribe

直接创建订阅（不经过支付流程）。

**注意**：此接口仅用于测试，生产环境应使用支付接口。

**请求**

```bash
curl -X POST https://www.mcptools.xin/api/v1/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "test_machine",
    "plan_type": "1m"
  }'
```

**响应**

```json
{
  "token": "xJd8fK2mL9pQ4vN7wR1sA6tB3uY5cZ0e",
  "expiry": "2026-02-08T14:30:45.123456"
}
```

---

## 套餐类型和价格

| 套餐代码 | 时长 | 价格 |
|---------|------|------|
| 1m | 1个月 | ¥29.90 |
| 3m | 3个月 | ¥79.90 |
| 6m | 6个月 | ¥149.90 |
| 12m | 12个月 | ¥269.90 |

---

## 数据更新频率

### 市场活跃度数据 (market-activity)

- **更新频率**：交易时间内每60秒更新一次
- **交易时间**：
  - 上午：09:30 - 11:30
  - 下午：13:00 - 15:00
- **交易日判断**：自动识别交易日，非交易日不更新

### 上交所汇总数据 (sse-summary)

- **更新频率**：每60秒更新一次
- **更新时间**：全天候更新

---

## 错误码

| HTTP状态码 | 说明 |
|-----------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（Token无效） |
| 403 | 禁止访问（订阅已过期或未激活） |
| 404 | 资源不found |
| 500 | 服务器内部错误 |

---

## 使用示例

### Python 示例

```python
import requests

class AIStockClient:
    def __init__(self, base_url="https://www.mcptools.xin"):
        self.base_url = base_url
        self.token = None
    
    def create_payment(self, machine_id, plan_type):
        """创建支付订单"""
        url = f"{self.base_url}/api/v1/payment/create-order"
        response = requests.post(url, json={
            "machine_id": machine_id,
            "plan_type": plan_type
        })
        return response.json()
    
    def check_payment(self, order_no):
        """查询支付状态"""
        url = f"{self.base_url}/api/v1/payment/order-status/{order_no}"
        return requests.get(url).json()
    
    def get_market_data(self):
        """获取市场数据"""
        url = f"{self.base_url}/api/v1/data/market-activity"
        response = requests.get(url, params={"token": self.token})
        return response.json()

# 使用示例
client = AIStockClient()

# 1. 创建订单
order = client.create_payment("my_machine_001", "1m")
print(f"订单号: {order['order_no']}")
print(f"支付金额: {order['amount']}")
print(f"二维码: {order['qr_code_url']}")

# 2. 轮询支付状态
import time
while True:
    status = client.check_payment(order['order_no'])
    if status['status'] == 'paid':
        client.token = status['token']
        print(f"支付成功！Token: {client.token}")
        break
    time.sleep(3)

# 3. 获取数据
data = client.get_market_data()
print(f"市场数据: {data}")
```

### JavaScript 示例

```javascript
class AIStockClient {
  constructor(baseUrl = 'https://www.mcptools.xin') {
    this.baseUrl = baseUrl;
    this.token = null;
  }
  
  async createPayment(machineId, planType) {
    const response = await fetch(`${this.baseUrl}/api/v1/payment/create-order`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ machine_id: machineId, plan_type: planType })
    });
    return await response.json();
  }
  
  async checkPayment(orderNo) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/payment/order-status/${orderNo}`
    );
    return await response.json();
  }
  
  async getMarketData() {
    const response = await fetch(
      `${this.baseUrl}/api/v1/data/market-activity?token=${this.token}`
    );
    return await response.json();
  }
}

// 使用示例
const client = new AIStockClient();

// 创建订单
const order = await client.createPayment('my_machine_001', '1m');
console.log('订单号:', order.order_no);
console.log('二维码:', order.qr_code_url);
```

---

## 后台管理

访问地址：`https://www.mcptools.xin/admin`

**功能**：
- 查看和管理订阅
- 查看支付订单
- 管理管理员用户

**默认账号**：
- 用户名：admin
- 密码：admin

**⚠️ 请在首次登录后立即修改密码！**

---

## 技术支持

- 文档仓库：查看项目README
- 问题反馈：联系技术支持
- 更新日志：查看CHANGELOG.md
