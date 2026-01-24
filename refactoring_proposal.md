# AIStockServer 重构架构建议书

本文档提供了对现有项目的重构建议，旨在解决当前的架构痛点，并提供更具扩展性和高性能的技术方案。

## 1. 现状痛点分析

基于代码审查，目前项目主要存在以下问题：

1.  **职责混淆**: `app/main.py` 和 `app/api/endpoints` 中混合了配置、业务逻辑和数据访问代码。
2.  **路由冲突**: `data` (数据分发) 和 `client` (客户端鉴权) 存在路径重叠，导致鉴权逻辑难以统一管理。
3.  **文件系统强耦合**: 代码中大量硬编码了文件路径 (`CACHE_DIR / "..."`)，难以测试，也难以切换存储后端。
4.  **同步阻塞风险**: 在异步接口 (`async def`) 中使用了大量的同步文件系统操作 (`path.exists()`, `glob()`)，在高并发下会阻塞 Event Loop，显著降低性能。
5.  **缺乏统一服务层**: 业务逻辑分散在各个路由函数中，无法复用。

## 2. 推荐架构设计

建议采用 **模块化单体 (Modular Monolith)** 配合 **读写分离 (CQRS)** 的架构模式。

### 2.1 核心分层 (Layers)

1.  **接入层 (Interface Layer/Transport)**:
    - **Nginx (反向代理)**: **关键优化点**。对于静态文件（CSV、图片等），直接由 Nginx 通过 `sendfile` 系统调用发送，实现真正的 "Zero-Copy"，不再经过 Python 应用层。Python 仅负责鉴权（通过 Nginx 的 `auth_request` 模块）。
    - **FastAPI**: 处理动态请求（API、管理后台、支付回调）。

2.  **应用服务层 (Application Service Layer)**:
    - `AuthService`: 统一处理 Token 验证、订阅状态检查。
    - `PaymentService`: 处理微信支付、订单状态流转。
    - `MarketDataService`: 数据查询逻辑的封装（但不负责重数据传输，仅负责元数据或即时数据）。

3.  **领域层 (Domain Layer)**:
    - 定义核心实体：`Subscription`, `Order`, `StockMetadata`.
    - 定义核心业务规则：如“订阅过期判定规则”。

4.  **基础设施层 (Infrastructure Layer)**:
    - **Repository**: 处理数据库操作 (`SQLAlchemy`)。
    - **StorageProvider**: 抽象文件存储接口。虽然最终是文件，但代码应该依赖接口而不是路径字符串。

### 2.2 数据流架构 (Data Flow)

我们将系统分为两个主要的数据流平面：

- **控制平面 (Control Plane)** - _低频，强一致性_
  - 处理：用户登录、订阅、支付、配置。
  - 技术：**PostgreSQL** (推荐) 或 SQLite (小规模)。
- **数据平面 (Data Plane)** - _高频，高性能_
  - 处理：行情分发、K线数据。
  - 技术：
    - **Redis**: 缓存热点数据（如最新一分钟的 Tick 数据、用户 Token）。
    - **File System + Nginx**: 负责大块数据（历史K线、全市场快照）的分发。

## 3. 技术栈推荐

| 组件            | 推荐技术                   | 理由                                                        |
| :-------------- | :------------------------- | :---------------------------------------------------------- |
| **编程语言**    | Python 3.10+               | 现有基础，生态丰富，Type Hint 支持完善。                    |
| **Web 框架**    | **FastAPI**                | 高性能异步框架，文档生成完善，便于前后端对接。              |
| **WSGI/ASGI**   | **Uvicorn** + **Gunicorn** | 生产环境标准配置，多 Workers 提升并发。                     |
| **反向代理**    | **Nginx**                  | **核心组件**。负责 SSL 卸载、静态资源托管、高并发文件分发。 |
| **数据库**      | **PostgreSQL**             | 比 SQLite 更适合并发写操作（订单+订阅），支持 JSONB。       |
| **缓存/热数据** | **Redis**                  | 保存 Token（设置 TTL 自动过期）、实时行情快照（Pub/Sub）。  |
| **ORM**         | **SQLAlchemy (Async)**     | 现代异步 ORM，支持类型提示。                                |
| **配置管理**    | **Pydantic Settings**      | 环境变量管理，类型安全。                                    |
| **任务队列**    | **ARQ** 或 **Celery**      | 处理微信支付回调、数据清洗等后台任务。                      |

## 4. 重构实施路线图 (Roadmap)

如果不希望一次性推翻重来，建议按以下步骤渐进式重构：

**第一阶段：基础设施标准化**

1.  引入 **Pydantic Settings** 统一管理所有配置（路径、密钥）。
2.  引入 **SQLAlchemy Async** 替换现有同步 DB 操作。

**第二阶段：服务层提取**

1.  创建 `services/` 目录，将 `endpoints/` 中的业务逻辑剥离出来。
2.  实现 `Dependency Injection`，将 Service 注入到 Router 中。

**第三阶段：高性能分发改造 (Nginx)**

1.  配置 Nginx 拦截 `/api/v1/data/kline` 等静态资源路径。
2.  编写 FastAPI 的 `/auth/verify` 接口。
3.  配置 Nginx 使用 `auth_request` 指令，先调用 FastAPI 鉴权，通过后直接由 Nginx 返回文件。

**第四阶段：数据源优化**

1.  将高频更新的实时数据（Currently CSV）改为写入 **Redis**。
2.  API 直接从 Redis 读取实时数据，极大降低磁盘 IO。

## 5. 目录结构示例

```text
app/
├── api/
│   ├── v1/
│   │   ├── endpoints/ # 仅包含路由定义和参数解析
│   │   └── dependencies.py # 鉴权依赖
├── core/ # 核心配置、异常处理
├── models/ # 数据库模型
├── schemas/ # Pydantic 数据校验模型
├── services/ # 核心业务逻辑
│   ├── payment_service.py
│   ├── auth_service.py
│   └── market_data_service.py
├── db/ # 数据库连接与 Repository
└── utils/
```
