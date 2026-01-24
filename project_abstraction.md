# AIStockServer 项目功能抽象与接口文档

## 1. 项目概述

AIStockServer 是一个基于 FastAPI 构建的高性能股票数据分发服务器。其主要定位是作为后端服务，为客户端提供实时行安、K线数据、资金流向等股票市场数据。项目采用了 "Zero-Copy" 的设计理念，通过直接通过文件流（FileResponse）分发缓存的 CSV 数据或 SQLite 数据，以最大化并发性能。

此外，项目还包含完整的订阅管理和微信支付集成功能，用于商业化运营。

## 2. 核心功能模块

### 2.1 股票数据分发 (Stock Data Distribution)

- **核心机制**: 不进行实时的数据采集（由独立的 Fetcher 进程负责），而是读取本地缓存目录 (`shared_cache`) 中的 CSV 文件或 SQLite 数据库。
- **数据类型**:
  - 实时行情 (Realtime Quote)
  - 历史/当日 K 线 (K-Line)
  - 市场情绪/赚钱效应 (Market Activity)
  - 上证指数概况 (SSE Summary)
  - 资金流向 (Fund Flow)
  - 盘口异动 (Stock Changes)
  - 股票列表 (Stock List)

### 2.2 订阅管理 (Client & Subscription)

- **机制**: 基于 Token 的鉴权机制。
- **功能**:
  - 订阅计划管理 (1个月, 3个月, 6个月, 12个月)
  - 机器码 (Machine ID) 绑定
  - Token 生成与验证

### 2.3 支付系统 (Payment)

- **集成**: 微信支付 (WeChat Pay Native模式)。
- **流程**: 创建订单 -> 获取二维码 -> 轮询/回调支付结果 -> 激活订阅。

### 2.4 管理后台 (Admin)

- **框架**: `sqladmin`
- **功能**: 提供可视化的界面管理订阅用户、支付订单和后台用户。

---

## 3. 接口定义 (API Reference)

_注：当前版本存在路由覆盖情况，`data` 路由优先于 `client` 路由加载，部分同名接口可能无需 Token 即可访问。_

### 3.1 基础接口 (System)

| 方法  | 路径           | 描述                                   |
| :---- | :------------- | :------------------------------------- |
| `GET` | `/`            | 服务运行状态检查                       |
| `GET` | `/health`      | 健康检查，返回缓存文件状态和交易日信息 |
| `GET` | `/sse-summary` | 获取上证指数概况 (快捷入口)            |

### 3.2 股票数据接口 (Stock Data)

**前缀**: `/api/v1`
**主要用途**: 高频数据获取，设计为直接读取缓存文件。

| 方法  | 路径                    | 参数                                        | 描述                                 |
| :---- | :---------------------- | :------------------------------------------ | :----------------------------------- |
| `GET` | `/data/kline`           | `symbol` (股票代码), `include_today` (bool) | 获取历史日线 K 线数据 (CSV)          |
| `GET` | `/data/kline/real`      | `symbol`                                    | 获取当日实时分钟级 K 线 (CSV/Memory) |
| `GET` | `/data/fund-flow`       | `symbol` (可选)                             | 获取资金流向数据                     |
| `GET` | `/data/stock-changes`   | `symbol` (可选)                             | 获取盘口异动数据                     |
| `GET` | `/data/stock-list`      | -                                           | 获取全市场股票基础信息表             |
| `GET` | `/data/status`          | -                                           | 获取服务端缓存文件的更新状态         |
| `GET` | `/data/market-activity` | -                                           | 获取市场赚钱效应数据 (公开)          |
| `GET` | `/data/sse-summary`     | -                                           | 获取上证指数概况 (公开)              |

### 3.3 客户端与鉴权接口 (Client)

**前缀**: `/api/v1`
**主要用途**: 用户订阅相关，从代码逻辑看，部分数据接口在此处定义了鉴权逻辑，但可能被 `Stock Data` 路由覆盖。

| 方法   | 路径                       | 参数                       | 描述                                      |
| :----- | :------------------------- | :------------------------- | :---------------------------------------- |
| `POST` | `/subscribe`               | `machine_id`, `plan_type`  | (测试用) 创建订阅并生成 Token             |
| `POST` | `/data/realtime-stocks`    | `stock_codes` (List)       | 获取指定股票列表的实时快照 (目前返回全量) |
| `GET`  | `/data/kline/{stock_code}` | `period`, `adjust`, `days` | 获取特定股票 K 线 (带参数校验)            |
| `GET`  | `/data/market-activity`    | `token`                    | (鉴权版) 获取市场赚钱效应                 |
| `GET`  | `/data/sse-summary`        | -                          | (鉴权版) 获取上证指数概况                 |
| `POST` | `/data/watch-stocks`       | -                          | (已弃用) 管理自选股                       |

### 3.4 支付接口 (Payment)

**前缀**: `/api/v1/payment`

| 方法   | 路径                       | 参数                      | 描述                             |
| :----- | :------------------------- | :------------------------ | :------------------------------- |
| `POST` | `/create-order`            | `machine_id`, `plan_type` | 创建微信支付订单，返回二维码链接 |
| `GET`  | `/order-status/{order_no}` | -                         | 查询订单支付状态及订阅结果       |
| `POST` | `/wechat/notify`           | XML Body                  | 微信支付异步回调入口             |

---

## 4. 数据模型 (Data Structure)

### 4.1 Subscription (订阅)

- `machine_id`: 机器唯一标识
- `token`: 访问令牌
- `plan_type`: 订阅类型 (1m/3m/6m/12m)
- `is_active`: 激活状态
- `end_date`: 过期时间

### 4.2 PaymentOrder (支付订单)

- `order_no`: 商户订单号
- `amount`: 金额
- `payment_status`: pending (待支付), paid (已支付), expired (过期), cancelled (取消)
- `wechat_transaction_id`: 微信侧订单号

## 5. 待重构建议 (Refactoring Notes)

基于当前代码分析，重构时建议关注以下点：

1.  **路由冲突**: `client` 和 `data` 中存在重复定义的路径（如 `/data/market-activity`），需统一规划。
2.  **鉴权统一**: 目前部分数据接口是公开的，部分尝试做鉴权，建议使用 FastAPI 的 `Dependencies` 做统一的路由级鉴权。
3.  **数据源抽象**: 目前强依赖文件系统路径，建议抽象 DataProvider 层，虽然目前是为了 Zero-Copy，但抽象层有助于测试和切换存储后端（如 Redis）。
4.  **配置管理**: 硬编码的路径较多，建议完善配置管理。
