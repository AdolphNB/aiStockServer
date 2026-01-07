# AIStock Remote Server (RemoteServer)

AIStock 的远程服务端工程，负责定时获取股票市场数据（资金流动、赚钱效应等），并为 PC 客户端提供订阅验证和数据分发服务。

## 1. 功能特性

- **定时数据抓取**: 在通过 `scheduler.py` 实现，仅在交易日（周一至周五）的 09:30-11:30 和 13:00-15:00 运行。
- **内存级缓存**: 获取的数据存储在服务端内存中，确保客户端获取时的低延迟。
- **订阅管理**: 提供 API 生成订阅 Token，通过 Token 验证客户端有效期。
- **后台管理**: 基于 `sqladmin` 的 Web 管理界面，方便手动激活用户和管理订阅。
- **API 服务**: 基于 FastAPI 的高性能异步接口。

## 2. 环境安装

推荐使用 `uv` 进行依赖管理，也可以使用标准的 `pip`。

### 方式 A: 使用 uv (推荐)

```bash
# 1. 安装 uv (如果未安装)
pip install uv

# 2. 创建虚拟环境
uv venv

# 3. 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. 安装依赖
uv pip install -r requirements.txt
```

### 方式 B: 使用标准 pip

```bash
pip install -r requirements.txt
```

## 3. 运行服务

### 本地开发运行

```bash
uvicorn main:app --reload
```

- **API 文档**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **后台管理**: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
  - 默认没有设置后台账号密码验证，生产环境请在 `config.py` 中加强安全配置。

### 生产环境部署 (Ubuntu)

建议使用 `gunicorn` 配合 `uvicorn` worker 运行，并使用 `Supervisor` 或 `Systemd` 进行进程守护。

```bash
# 启动命令示例 (4个 worker)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

配置 Nginx 反向代理，将域名 `mcptools.xin` 指向本地 8000 端口。

## 4. API 接口说明

### 4.1 订阅 (模拟)

- **POST** `/api/v1/subscribe`
- **Body**: `{"machine_id": "xxxx", "plan_type": "1m"}`
- **返回**: `{"token": "secure_token_string", "expiry": "2026-..."}`

### 4.2 获取市场数据

- **GET** `/api/v1/data/market-activity?token=YOUR_TOKEN`
- **说明**: Token 必须有效且在订阅期内。
- **使用场景**: 客户端定时轮询此接口获取最新的赚钱效应数据。

## 5. 项目结构

```
remoteServer/
├── config.py           # 配置文件 (数据库、密钥等)
├── database.py         # 数据库连接
├── fetcher.py          # 数据抓取逻辑 (线程安全)
├── main.py             # FastAPI 入口
├── models.py           # 数据库模型
├── scheduler.py        # 定时任务调度
├── requirements.txt    # 项目依赖
└── routers/            # API 路由模块
    └── client.py       # 客户端相关接口
```

## 6. 注意事项

1.  **数据覆盖**: 每次定时任务执行时，内存中的数据会被最新数据完全覆盖。
2.  **线程安全**: `fetcher.py` 内部使用了 `threading.Lock`，确保数据写入和 API 读取时的并发安全。
3.  **时区**: 默认使用服务器本地时间，请确保服务器时区设置为 `Asia/Shanghai` 以保证交易时间判断准确。
