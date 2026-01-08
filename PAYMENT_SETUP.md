# 微信支付配置指南

本文档详细说明如何配置微信支付功能。

## 前置条件

1. 已完成微信支付商户号申请
2. 拥有微信公众号或小程序（用于获取AppID）
3. 已完成商户认证

## 1. 获取微信支付凭证

### 1.1 登录微信支付商户平台

访问：https://pay.weixin.qq.com/

### 1.2 获取商户号（MCHID）

- 登录后在【账户中心】->【商户信息】中查看
- 格式：10位数字，例如：1234567890

### 1.3 获取AppID

- 如果使用公众号：在【公众号设置】->【基本设置】中查看
- 如果使用小程序：在【小程序设置】->【基本设置】中查看
- 格式：wx开头的字符串，例如：wxabcdef1234567890

### 1.4 设置API密钥（V2）

1. 进入【账户中心】->【API安全】->【设置密钥】
2. 设置32位的API密钥（建议使用强随机密码）
3. 妥善保存，该密钥不可找回，只能重新设置

**重要**：API密钥是敏感信息，切勿泄露！

### 1.5 配置支付授权目录

1. 进入【产品中心】->【开发配置】
2. 添加支付授权目录：
   ```
   https://www.mcptools.xin/api/v1/payment/
   ```

### 1.6 配置回调通知URL

在创建订单时会自动使用配置的回调URL：
```
https://www.mcptools.xin/api/v1/payment/wechat/notify
```

确保该URL可以从外网访问（微信服务器需要调用）。

## 2. 配置服务器环境变量

### 2.1 编辑环境变量文件

在服务器上编辑 `/opt/aistock/.env` 文件：

```bash
sudo nano /opt/aistock/.env
```

### 2.2 添加微信支付配置

```bash
# WeChat Pay Configuration
WECHAT_APPID=wx1234567890abcdef      # 替换为实际的AppID
WECHAT_MCHID=1234567890              # 替换为实际的商户号
WECHAT_API_KEY=your32characterapikey  # 替换为实际的API密钥
SERVER_URL=https://www.mcptools.xin   # 服务器公网URL
```

### 2.3 保存并重启服务

```bash
# 重启服务使配置生效
sudo systemctl restart aistock

# 检查服务状态
sudo systemctl status aistock
```

## 3. 测试支付功能

### 3.1 使用测试模式

如果尚未配置微信支付凭证，系统会自动使用Mock模式进行测试。

### 3.2 创建测试订单

```bash
# 使用curl测试创建订单
curl -X POST "https://www.mcptools.xin/api/v1/payment/create-order" \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "test_machine_001",
    "plan_type": "1m"
  }'
```

期望返回：
```json
{
  "order_no": "ORDER_20260108123456_ABC123",
  "amount": 29.9,
  "qr_code_url": "weixin://wxpay/bizpayurl?pr=xxx",
  "expires_at": "2026-01-08T14:34:56",
  "plan_type": "1m"
}
```

### 3.3 查询订单状态

```bash
curl "https://www.mcptools.xin/api/v1/payment/order-status/ORDER_20260108123456_ABC123"
```

### 3.4 测试完整支付流程

使用提供的客户端示例脚本：

```bash
# 安装依赖
pip install requests qrcode[pil]

# 运行测试
python CLIENT_EXAMPLE.py
```

## 4. 套餐价格配置

当前套餐价格在 `app/core/config.py` 中定义：

```python
PLAN_PRICES: dict = {
    "1m": 29.90,   # 1个月
    "3m": 79.90,   # 3个月
    "6m": 149.90,  # 6个月
    "12m": 269.90  # 12个月
}
```

如需修改价格：

1. 编辑 `app/core/config.py`
2. 修改对应套餐的价格
3. 重启服务

或者通过环境变量覆盖：

```bash
# 在 .env 文件中添加
PLAN_PRICES='{"1m": 19.90, "3m": 49.90, "6m": 89.90, "12m": 159.90}'
```

## 5. 支付流程说明

### 5.1 完整支付流程

```
客户端                     服务器                    微信支付
  |                         |                          |
  |--1.创建订单------------>|                          |
  |                         |--2.统一下单API---------->|
  |                         |<--3.返回code_url---------|
  |<--4.返回二维码URL-------|                          |
  |                         |                          |
  |--5.显示二维码           |                          |
  |                         |                          |
  |   [用户扫码支付]        |                          |
  |                         |                          |
  |                         |<--6.支付成功通知---------|
  |                         |--7.创建订阅记录          |
  |                         |--8.返回成功确认--------->|
  |                         |                          |
  |--9.轮询查询订单状态---->|                          |
  |<--10.返回token----------|                          |
  |                         |                          |
  |--11.使用token获取数据-->|                          |
  |<--12.返回股票数据-------|                          |
```

### 5.2 订单状态说明

| 状态 | 说明 |
|------|------|
| pending | 待支付 |
| paid | 已支付 |
| expired | 已过期（2小时未支付） |
| cancelled | 已取消 |

## 6. 安全建议

### 6.1 保护敏感信息

```bash
# 确保环境变量文件权限正确
sudo chmod 600 /opt/aistock/.env
sudo chown aistock:aistock /opt/aistock/.env
```

### 6.2 配置HTTPS

微信支付**必须**使用HTTPS，确保：

1. SSL证书有效
2. 回调URL使用HTTPS
3. 证书不过期（配置自动续期）

### 6.3 IP白名单

在微信支付商户平台配置服务器IP白名单：

1. 【账户中心】->【API安全】->【设置API密钥】
2. 添加服务器公网IP

### 6.4 定期更换密钥

建议每3-6个月更换一次API密钥。

## 7. 常见问题

### Q1: 支付回调收不到

**原因**：
- 服务器防火墙阻止
- 回调URL配置错误
- HTTPS证书问题

**解决**：
1. 确保回调URL可以从外网访问
2. 检查Nginx配置
3. 查看服务器日志：`sudo journalctl -u aistock -f | grep notify`

### Q2: 签名验证失败

**原因**：
- API密钥配置错误
- 参数编码问题

**解决**：
1. 确认API密钥配置正确
2. 检查日志中的详细错误信息

### Q3: 订单创建失败

**原因**：
- 商户号配置错误
- 网络问题
- 微信支付接口异常

**解决**：
1. 检查WECHAT_APPID、WECHAT_MCHID、WECHAT_API_KEY配置
2. 查看详细错误日志
3. 确认商户号状态正常

### Q4: 如何退款

当前版本未实现退款功能。如需退款，请：

1. 登录微信支付商户平台
2. 在【交易中心】->【订单查询】中找到订单
3. 手动操作退款
4. 在后台管理界面中取消对应的订阅

## 8. 监控和日志

### 8.1 查看支付相关日志

```bash
# 查看所有支付相关日志
sudo journalctl -u aistock -f | grep -i payment

# 查看微信支付回调日志
sudo journalctl -u aistock -f | grep -i wechat

# 查看订单创建日志
sudo journalctl -u aistock -f | grep "Payment order created"
```

### 8.2 数据库查询

```bash
# 进入Python shell
sudo -u aistock /opt/aistock/venv/bin/python

# 查询订单
from app.core.database import SessionLocal
from app.models.models import PaymentOrder
db = SessionLocal()
orders = db.query(PaymentOrder).order_by(PaymentOrder.created_at.desc()).limit(10).all()
for order in orders:
    print(f"{order.order_no} - {order.payment_status} - {order.amount}")
```

## 9. 参考资料

- [微信支付官方文档](https://pay.weixin.qq.com/wiki/doc/api/index.html)
- [Native支付API文档](https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=6_1)
- [支付结果通知](https://pay.weixin.qq.com/wiki/doc/api/native.php?chapter=9_7&index=8)

## 10. 技术支持

如遇到问题：

1. 查看本文档的常见问题部分
2. 检查服务器日志
3. 查看微信支付商户平台的错误信息
4. 联系技术支持
