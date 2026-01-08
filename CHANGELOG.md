# 更新日志

## [2.0.0] - 2026-01-08

### ✨ 新增功能

#### 1. 微信支付集成
- ✅ 实现微信Native支付（扫码支付）
- ✅ 支付订单管理系统
- ✅ 支付回调处理
- ✅ 自动激活订阅
- ✅ Mock支付服务（用于测试）

**新增文件**：
- `app/services/wechat_pay.py` - 微信支付服务
- `app/api/endpoints/payment.py` - 支付API接口

**新增API**：
- `POST /api/v1/payment/create-order` - 创建支付订单
- `GET /api/v1/payment/order-status/{order_no}` - 查询订单状态
- `POST /api/v1/payment/wechat/notify` - 微信支付回调

#### 2. 交易日历功能
- ✅ 使用akshare获取交易日历
- ✅ 自动识别交易日
- ✅ 只在交易日和交易时间段内获取数据
- ✅ 交易日缓存机制（24小时更新）

**新增文件**：
- `app/services/trading_calendar.py` - 交易日历服务

#### 3. 支付订单数据模型
- ✅ 新增 `PaymentOrder` 模型
- ✅ 订单与订阅关联
- ✅ 支持多种订单状态（pending/paid/expired/cancelled）

**修改文件**：
- `app/models/models.py` - 添加 PaymentOrder 模型

#### 4. 后台管理增强
- ✅ 添加支付订单管理
- ✅ 可查看订单详情
- ✅ 支持订单搜索

#### 5. 部署配置
- ✅ Nginx配置示例（支持负载均衡）
- ✅ Systemd服务配置
- ✅ 多Worker启动脚本
- ✅ 完整的部署指南

**新增文件**：
- `deployment/nginx.conf` - Nginx配置
- `deployment/systemd_service.conf` - Systemd服务配置
- `deployment/multi_worker_setup.sh` - 多进程管理脚本
- `deployment/DEPLOYMENT_GUIDE.md` - 详细部署指南

#### 6. 文档完善
- ✅ API使用文档
- ✅ 微信支付配置指南
- ✅ 客户端示例代码
- ✅ 更新日志

**新增文件**：
- `API_DOCUMENTATION.md` - API完整文档
- `PAYMENT_SETUP.md` - 支付配置指南
- `CLIENT_EXAMPLE.py` - Python客户端示例
- `CHANGELOG.md` - 本文件

### 🔧 改进

#### 配置系统
- ✅ 新增微信支付配置项
- ✅ 新增服务器URL配置
- ✅ 套餐价格可配置

**修改文件**：
- `app/core/config.py`

#### 定时任务
- ✅ 集成交易日判断
- ✅ 只在交易时间获取数据

**修改文件**：
- `app/services/scheduler.py`

#### 健康检查
- ✅ 添加交易日状态
- ✅ 添加交易日历缓存信息

**修改文件**：
- `app/main.py`

#### 依赖更新
- ✅ 添加lxml（用于XML解析）
- ✅ 更新requests版本

**修改文件**：
- `requirements.txt`

### 🏗️ 架构改进

#### 负载均衡支持
- ✅ 支持Gunicorn多worker模式
- ✅ Nginx反向代理配置
- ✅ 可支持20+并发用户

#### 数据库结构
- ✅ 订单与订阅关联关系
- ✅ 支付状态管理
- ✅ 时间戳记录

### 📊 数据流程

#### 新的订阅流程
```
1. 客户端创建支付订单
2. 服务器返回二维码URL
3. 用户扫码支付
4. 微信回调通知服务器
5. 服务器自动创建订阅并生成token
6. 客户端轮询获取token
7. 使用token访问数据
```

#### 旧的订阅流程（保留用于测试）
```
1. 客户端直接调用订阅接口
2. 服务器立即生成token
```

### 🔐 安全性增强

- ✅ 微信支付签名验证
- ✅ Token安全生成
- ✅ HTTPS强制
- ✅ 环境变量保护

### 📈 性能优化

- ✅ 交易日历缓存（减少API调用）
- ✅ 多worker负载均衡
- ✅ Nginx反向代理
- ✅ 连接池管理

### 🐛 Bug修复

- 修复：交易日判断不准确（之前只判断时间，不判断日期）
- 改进：数据缓存线程安全

### 📝 待办事项（未来版本）

- [ ] 支持支付宝支付
- [ ] 实现退款功能
- [ ] 添加数据推送功能（WebSocket）
- [ ] 更多股票数据接口
- [ ] 用户使用统计
- [ ] 邮件通知功能
- [ ] 微信公众号集成

---

## [1.0.0] - 初始版本

### 基础功能

- ✅ FastAPI服务器框架
- ✅ SQLite数据库
- ✅ 订阅管理系统
- ✅ 市场活跃度数据获取（akshare）
- ✅ 上交所汇总数据获取
- ✅ 定时任务调度
- ✅ 后台管理界面
- ✅ Token认证机制
