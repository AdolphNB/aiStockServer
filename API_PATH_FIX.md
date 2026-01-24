# API 路径修复说明

## 问题描述

从终端日志中发现，客户端正在使用错误的API路径，导致404错误：

```
404错误：
- GET /api/data/stock-changes
- GET /api/data/stock-list  
- GET /api/data/market-activity
- GET /api/data/sse-summary
- GET /api/data/kline/rea
- GET /api/data/kline/real
```

## 正确的API路径

所有数据接口都应该使用 `/api/v1` 前缀：

### ✅ 正确的路径

| 功能 | 正确路径 | 错误路径 |
|------|----------|----------|
| 股票列表 | `/api/v1/data/stock-list` | `/api/data/stock-list` |
| 盘口异动 | `/api/v1/data/stock-changes` | `/api/data/stock-changes` |
| 市场活动 | `/api/v1/data/market-activity` | `/api/data/market-activity` |
| 上证概况 | `/api/v1/data/sse-summary` | `/api/data/sse-summary` |
| 实时K线 | `/api/v1/data/kline/real?symbol=XXX` | `/api/data/kline/real` |
| 历史K线 | `/api/v1/data/kline?symbol=XXX` | `/api/data/kline` |
| 资金流向 | `/api/v1/data/fund-flow` | `/api/data/fund-flow` |
| 数据状态 | `/api/v1/data/status` | `/api/data/status` |

## 完整的API端点列表

### 1. 数据查询接口

```bash
# 股票列表
GET http://your-server:8000/api/v1/data/stock-list

# 历史K线（需要symbol参数）
GET http://your-server:8000/api/v1/data/kline?symbol=688595&include_today=true

# 实时K线（需要symbol参数）
GET http://your-server:8000/api/v1/data/kline/real?symbol=688595

# 资金流向（可选symbol参数）
GET http://your-server:8000/api/v1/data/fund-flow
GET http://your-server:8000/api/v1/data/fund-flow?symbol=688595

# 盘口异动（可选symbol参数）
GET http://your-server:8000/api/v1/data/stock-changes
GET http://your-server:8000/api/v1/data/stock-changes?symbol=688595

# 市场活动（赚钱效应）
GET http://your-server:8000/api/v1/data/market-activity

# 上证指数概况
GET http://your-server:8000/api/v1/data/sse-summary

# 数据状态
GET http://your-server:8000/api/v1/data/status
```

### 2. 系统状态接口

```bash
# 根路径（检查服务是否运行）
GET http://your-server:8000/

# 健康检查
GET http://your-server:8000/health

# 快捷SSE概况（根路径）
GET http://your-server:8000/sse-summary
```

## 客户端修改建议

### 修改前（错误）：
```python
# 错误示例
base_url = "http://server:8000/api/data"
stock_list_url = f"{base_url}/stock-list"  # 错误！
```

### 修改后（正确）：
```python
# 正确示例
base_url = "http://server:8000/api/v1/data"
stock_list_url = f"{base_url}/stock-list"  # 正确！
```

## 测试验证

使用 curl 测试所有接口：

```bash
# 设置服务器地址
SERVER="http://your-server:8000"

# 测试所有数据接口
curl "$SERVER/api/v1/data/stock-list"
curl "$SERVER/api/v1/data/kline?symbol=688595"
curl "$SERVER/api/v1/data/kline/real?symbol=688595"
curl "$SERVER/api/v1/data/fund-flow"
curl "$SERVER/api/v1/data/stock-changes"
curl "$SERVER/api/v1/data/market-activity"
curl "$SERVER/api/v1/data/sse-summary"
curl "$SERVER/api/v1/data/status"

# 测试系统接口
curl "$SERVER/"
curl "$SERVER/health"
curl "$SERVER/sse-summary"
```

## 注意事项

1. **版本前缀是必需的**：所有数据接口都必须包含 `/api/v1` 前缀
2. **参数大小写敏感**：URL参数（如 `symbol`）是小写的
3. **符号代码格式**：股票代码应该是6位数字，如 `688595` 或 `000001`
4. **响应格式**：
   - 大部分接口返回 CSV 格式（`text/csv`）
   - 状态接口返回 JSON 格式

## 常见错误和解决方案

### 错误 1：404 Not Found
```
GET /api/data/stock-list -> 404
```
**解决**：添加 `/v1` → `/api/v1/data/stock-list`

### 错误 2：缺少必需参数
```
GET /api/v1/data/kline -> 422 或 400
```
**解决**：添加 symbol 参数 → `/api/v1/data/kline?symbol=688595`

### 错误 3：股票代码格式错误
```
GET /api/v1/data/kline?symbol=1 -> 可能返回不正确的数据
```
**解决**：使用6位格式 → `symbol=000001`

## API文档位置

完整的API文档可以访问：
```bash
# 访问 FastAPI 自动生成的文档
http://your-server:8000/docs

# 或者 ReDoc 格式
http://your-server:8000/redoc
```

## 支持

如有问题，请检查：
1. 服务器日志：查看具体的错误信息
2. API文档：访问 `/docs` 查看所有可用接口
3. 健康检查：访问 `/health` 确认服务状态
