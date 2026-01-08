# AIStock Remote Server

AIStock 的远程服务端工程，负责定时获取股票市场数据（资金流动、赚钱效应等），并为 PC 客户端提供订阅验证和数据分发服务。

## 1. 功能特性

### 核心功能
- **定时数据抓取**: 通过 `scheduler.py` 实现，自动识别交易日，仅在交易时间（09:30-11:30, 13:00-15:00）运行
- **交易日历**: 使用akshare获取实时交易日历，自动判断交易日和节假日
- **内存级缓存**: 获取的数据存储在服务端内存中，确保客户端获取时的低延迟
- **微信支付集成**: 完整的微信Native支付（扫码支付）流程，自动激活订阅
- **订阅管理**: 多种订阅套餐（1/3/6/12月），基于Token的认证机制
- **后台管理**: 基于 `sqladmin` 的 Web 管理界面，管理订阅、订单和用户
- **高性能API**: 基于 FastAPI 的异步接口，支持负载均衡和并发访问
- **生产就绪**: 提供完整的Nginx、Systemd配置，支持HTTPS和多Worker部署

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

## 4. 快速开始

### 4.1 本地测试（使用Mock支付）

```bash
# 启动服务
python -m app.main

# 或使用uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：
- API文档: http://localhost:8000/docs
- 后台管理: http://localhost:8000/admin (默认: admin/admin)
- 健康检查: http://localhost:8000/health

### 4.2 生产部署

详细部署指南请查看: [deployment/DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md)

简要步骤：
1. 配置微信支付参数（查看 [PAYMENT_SETUP.md](PAYMENT_SETUP.md)）
2. 部署到Ubuntu服务器
3. 配置Nginx反向代理和SSL证书
4. 使用Systemd管理服务

## 5. API 接口说明

完整API文档: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

### 5.1 支付和订阅

#### 创建支付订单
```bash
POST /api/v1/payment/create-order
Body: {"machine_id": "your_machine_id", "plan_type": "1m"}
返回: {"order_no": "...", "qr_code_url": "weixin://...", "amount": 29.9}
```

#### 查询订单状态
```bash
GET /api/v1/payment/order-status/{order_no}
返回: {"status": "paid", "token": "...", "subscription_end_date": "..."}
```

### 5.2 获取数据

#### 市场活跃度数据（需要Token）
```bash
GET /api/v1/data/market-activity?token=YOUR_TOKEN
返回: {"timestamp": "...", "data": [...]}
```

#### 上交所汇总数据（公开接口）
```bash
GET /sse-summary
返回: {"timestamp": "...", "data": [...]}
```

### 5.3 套餐价格

| 套餐 | 时长 | 价格 |
|------|------|------|
| 1m | 1个月 | ¥29.90 |
| 3m | 3个月 | ¥79.90 |
| 6m | 6个月 | ¥149.90 |
| 12m | 12个月 | ¥269.90 |

## 6. 客户端示例

查看 [CLIENT_EXAMPLE.py](CLIENT_EXAMPLE.py) 了解如何：
- 创建支付订单并显示二维码
- 轮询查询支付状态
- 使用Token获取数据

```python
from CLIENT_EXAMPLE import AIStockClient

client = AIStockClient("https://www.mcptools.xin")
# 创建订单、等待支付、获取数据...
```

## 7. 项目结构

```
aiStockServer/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI应用入口
│   ├── api/
│   │   └── endpoints/
│   │       ├── client.py          # 客户端数据接口
│   │       └── payment.py         # 支付相关接口
│   ├── core/
│   │   ├── config.py              # 配置管理
│   │   └── database.py            # 数据库连接
│   ├── models/
│   │   └── models.py              # 数据模型（Subscription, PaymentOrder等）
│   └── services/
│       ├── fetcher.py             # 数据获取服务（akshare）
│       ├── scheduler.py           # 定时任务调度
│       ├── wechat_pay.py          # 微信支付服务
│       └── trading_calendar.py   # 交易日历服务
├── deployment/                     # 部署配置文件
│   ├── nginx.conf                 # Nginx配置
│   ├── systemd_service.conf       # Systemd服务配置
│   ├── multi_worker_setup.sh      # 多Worker管理脚本
│   └── DEPLOYMENT_GUIDE.md        # 详细部署指南
├── tests/                          # 测试文件
├── requirements.txt                # Python依赖
├── CLIENT_EXAMPLE.py              # 客户端示例代码
├── API_DOCUMENTATION.md           # API完整文档
├── PAYMENT_SETUP.md               # 微信支付配置指南
└── README.md                      # 本文件
```

## 8. 数据更新机制

### 市场活跃度数据
- **数据源**: akshare - `stock_market_activity_legu()`
- **更新频率**: 交易时间内每60秒
- **交易时间**: 09:30-11:30, 13:00-15:00
- **交易日判断**: 使用akshare交易日历自动识别

### 上交所汇总数据
- **数据源**: akshare - `stock_sse_summary()`
- **更新频率**: 每60秒（全天）

## 9. 技术栈

- **Web框架**: FastAPI
- **ASGI服务器**: Uvicorn / Gunicorn
- **数据库**: SQLite（可升级为PostgreSQL/MySQL）
- **ORM**: SQLAlchemy
- **定时任务**: APScheduler
- **数据源**: akshare
- **支付**: 微信支付 Native API
- **后台管理**: SQLAdmin
- **反向代理**: Nginx

## 10. 安全特性

- ✅ HTTPS强制
- ✅ Token认证机制
- ✅ 微信支付签名验证
- ✅ 环境变量保护敏感信息
- ✅ SQL注入防护（SQLAlchemy ORM）
- ✅ 速率限制（Nginx配置）

## 11. 性能指标

- **并发支持**: 20+ 用户同时访问
- **响应时间**: < 100ms（数据查询）
- **数据更新延迟**: 60秒
- **可用性**: 支持多Worker负载均衡

## 12. 文档索引

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 本文件，项目概览 |
| [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | 完整API接口文档 |
| [PAYMENT_SETUP.md](PAYMENT_SETUP.md) | 微信支付配置指南 |
| [deployment/DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) | 生产环境部署指南 |
| [CLIENT_EXAMPLE.py](CLIENT_EXAMPLE.py) | Python客户端示例 |
| [CHANGELOG.md](CHANGELOG.md) | 版本更新日志 |
| [TEST_GUIDE.md](TEST_GUIDE.md) | 测试指南 |

## 13. 常见问题

### Q: 如何测试支付功能？
A: 如果未配置微信支付凭证，系统会自动使用Mock模式。查看 [PAYMENT_SETUP.md](PAYMENT_SETUP.md)

### Q: 如何修改套餐价格？
A: 编辑 `app/core/config.py` 中的 `PLAN_PRICES` 字典，或通过环境变量配置。

### Q: 如何支持更多并发用户？
A: 增加Gunicorn的worker数量，或部署多个实例配合Nginx负载均衡。查看部署指南。

### Q: 数据不更新怎么办？
A: 检查是否为交易日和交易时间，查看 `/health` 接口的 `is_trading_day` 字段。

### Q: 如何备份数据？
A: SQLite数据库文件位于 `aistock.db`，定期备份即可。生产环境建议使用PostgreSQL。

## 14. 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本历史和更新内容。

## 15. 许可证

查看 [LICENSE](LICENSE) 文件。

## 16. 支持

- 问题反馈: 提交Issue
- 技术支持: 联系开发团队
- 文档更新: 欢迎PR
