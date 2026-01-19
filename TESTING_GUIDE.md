# 测试指南

## 快速启动和测试

### 1. 启动服务

```bash
# 使用 uv 环境
cd /root/aiStockServer
source .venv/bin/activate  # 如果使用虚拟环境
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. 初始化数据（首次使用）

由于数据是定时获取的，首次启动后需要手动触发数据获取进行测试：

```bash
# 1. 获取股票列表
curl -X POST http://localhost:8000/api/v1/data/fetch/stock-list

# 2. 获取实时数据（需要3-5秒）
curl -X POST http://localhost:8000/api/v1/data/fetch/realtime

# 3. 获取资金流向
curl -X POST http://localhost:8000/api/v1/data/fetch/fund-flow

# 4. 获取盘口异动
curl -X POST http://localhost:8000/api/v1/data/fetch/stock-changes
```

### 3. 验证数据状态

```bash
# 查看系统状态
curl http://localhost:8000/api/v1/data/status
```

### 4. 测试查询接口

```bash
# 获取股票列表
curl http://localhost:8000/api/v1/data/stock-list

# 获取历史K线（平安银行）
curl "http://localhost:8000/api/v1/data/kline?symbol=000001"

# 获取实时分时数据
curl "http://localhost:8000/api/v1/data/kline/real?symbol=000001"

# 获取资金流向
curl "http://localhost:8000/api/v1/data/fund-flow?symbol=000001"

# 获取盘口异动
curl "http://localhost:8000/api/v1/data/stock-changes?symbol=000001"
```

## 完整测试流程

### 使用 Python 脚本测试

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

print("=== 开始初始化数据 ===")

# 1. 获取股票列表
print("\n1. 获取股票列表...")
response = requests.post(f"{BASE_URL}/data/fetch/stock-list")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# 2. 获取实时数据（需要时间）
print("\n2. 获取实时数据（这可能需要3-5秒）...")
response = requests.post(f"{BASE_URL}/data/fetch/realtime")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# 3. 获取资金流向
print("\n3. 获取资金流向...")
response = requests.post(f"{BASE_URL}/data/fetch/fund-flow")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# 4. 获取盘口异动
print("\n4. 获取盘口异动...")
response = requests.post(f"{BASE_URL}/data/fetch/stock-changes")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

print("\n=== 数据初始化完成 ===")

# 等待一下，确保数据已处理
time.sleep(2)

print("\n=== 开始测试查询接口 ===")

# 测试查询
print("\n查询实时分时数据（000001）...")
response = requests.get(f"{BASE_URL}/data/kline/real?symbol=000001")
data = response.json()
print(f"Code: {data['code']}")
print(f"Message: {data['message']}")
if data['data']:
    print(f"数据行数: {len(data['data']['data'])}")
    print(f"列名: {data['data']['columns']}")

print("\n查询资金流向（000001）...")
response = requests.get(f"{BASE_URL}/data/fund-flow?symbol=000001")
data = response.json()
print(f"Code: {data['code']}")
print(f"Message: {data['message']}")

print("\n查询盘口异动（000001）...")
response = requests.get(f"{BASE_URL}/data/stock-changes?symbol=000001")
data = response.json()
print(f"Code: {data['code']}")
print(f"Message: {data['message']}")

print("\n=== 测试完成 ===")
```

## 使用浏览器测试

### 1. 访问 API 文档

打开浏览器访问: http://localhost:8000/docs

### 2. 手动触发数据获取

在 API 文档中找到以下端点并执行：

- `POST /api/v1/data/fetch/stock-list` - 获取股票列表
- `POST /api/v1/data/fetch/realtime` - 获取实时数据
- `POST /api/v1/data/fetch/fund-flow` - 获取资金流向
- `POST /api/v1/data/fetch/stock-changes` - 获取盘口异动

### 3. 查看数据状态

访问: `GET /api/v1/data/status`

### 4. 测试查询接口

- `GET /api/v1/data/kline?symbol=000001` - 历史K线
- `GET /api/v1/data/kline/real?symbol=000001` - 实时分时
- `GET /api/v1/data/fund-flow?symbol=000001` - 资金流向
- `GET /api/v1/data/stock-changes?symbol=000001` - 盘口异动

## 路由冲突问题已修复

### 问题描述

之前 `/api/v1/data/kline/real` 被 `/api/v1/data/kline/{stock_code}` 路由拦截。

### 解决方案

调整了路由注册顺序，将新的 `data.router` 注册在 `client.router` 之前。

## 常见问题

### Q: 为什么查询返回 404 No data found?

**A**: 数据还没有被获取。有两种情况：

1. **服务刚启动**: 需要等待定时任务执行，或手动触发数据获取
2. **非交易时段**: 某些数据只在交易时段更新

**解决方法**: 使用 POST 接口手动触发数据获取：

```bash
curl -X POST http://localhost:8000/api/v1/data/fetch/fund-flow
curl -X POST http://localhost:8000/api/v1/data/fetch/stock-changes
```

### Q: 实时数据获取很慢？

**A**: 这是正常的。`ak.stock_zh_a_spot_em()` 需要获取全市场5000+只股票的数据，通常需要3-5秒。

### Q: 如何查看当前有多少数据？

**A**: 访问状态端点：

```bash
curl http://localhost:8000/api/v1/data/status
```

### Q: 历史K线数据从哪里来？

**A**: 历史K线数据按需获取：

- 首次请求时从 akshare 获取并缓存
- 后续请求从内存缓存读取
- 当天的K线从实时数据计算得出

### Q: 如何清空并重新获取数据？

**A**: 重启服务即可清空内存数据，然后重新手动触发获取。

## 性能测试

### 测试响应时间

```bash
# 测试历史K线查询（应该很快，毫秒级）
time curl "http://localhost:8000/api/v1/data/kline?symbol=000001"

# 测试实时数据查询（应该很快，毫秒级）
time curl "http://localhost:8000/api/v1/data/kline/real?symbol=000001"

# 测试数据获取（较慢，3-5秒）
time curl -X POST "http://localhost:8000/api/v1/data/fetch/realtime"
```

### 并发测试

```bash
# 使用 ab (Apache Bench)
ab -n 100 -c 10 "http://localhost:8000/api/v1/data/kline?symbol=000001"

# 使用 wrk
wrk -t4 -c100 -d30s "http://localhost:8000/api/v1/data/kline?symbol=000001"
```

## 自动化测试脚本

保存以下内容为 `test_all_apis.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"

echo "=========================================="
echo "Stock Data API - Complete Test Suite"
echo "=========================================="

echo ""
echo "Step 1: Initialize Data..."
echo "------------------------------------------"

echo "Fetching stock list..."
curl -s -X POST "$BASE_URL/data/fetch/stock-list" | jq .

echo ""
echo "Fetching realtime data (this may take 3-5 seconds)..."
curl -s -X POST "$BASE_URL/data/fetch/realtime" | jq .

echo ""
echo "Fetching fund flow data..."
curl -s -X POST "$BASE_URL/data/fetch/fund-flow" | jq .

echo ""
echo "Fetching stock changes data..."
curl -s -X POST "$BASE_URL/data/fetch/stock-changes" | jq .

echo ""
echo "Step 2: Check System Status..."
echo "------------------------------------------"
curl -s "$BASE_URL/data/status" | jq .

echo ""
echo "Step 3: Test Query APIs..."
echo "------------------------------------------"

echo ""
echo "Testing: Stock List"
curl -s "$BASE_URL/data/stock-list" | jq '.code, .message, (.data.data | length)'

echo ""
echo "Testing: Historical K-line (000001)"
curl -s "$BASE_URL/data/kline?symbol=000001" | jq '.code, .message, (.data.data | length)'

echo ""
echo "Testing: Realtime K-line (000001)"
curl -s "$BASE_URL/data/kline/real?symbol=000001" | jq '.code, .message'

echo ""
echo "Testing: Fund Flow (000001)"
curl -s "$BASE_URL/data/fund-flow?symbol=000001" | jq '.code, .message'

echo ""
echo "Testing: Stock Changes (000001)"
curl -s "$BASE_URL/data/stock-changes?symbol=000001" | jq '.code, .message'

echo ""
echo "=========================================="
echo "All tests completed!"
echo "=========================================="
```

运行测试：

```bash
chmod +x test_all_apis.sh
./test_all_apis.sh
```

## 下一步

测试通过后：

1. 查看 `DEPLOYMENT.md` 了解生产环境部署
2. 查看 `STOCK_DATA_API.md` 了解完整API文档
3. 配置 systemd 服务自动启动
4. 配置 Nginx 反向代理
5. 设置监控和告警
