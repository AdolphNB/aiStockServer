# 快速启动指南

## 前置要求

- Python 3.8+
- 已安装所有依赖包（见 `requirements.txt`）

## 启动步骤

### 1. 初始化数据目录

首次运行需要创建数据目录结构：

```bash
python init_data_dirs.py
```

### 2. 启动服务

```bash
# 方式1: 使用 uvicorn 直接启动
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 方式2: 使用 Python 模块方式启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 方式3: 直接运行 main.py
python app/main.py
```

### 3. 验证服务

在浏览器中访问：

- 健康检查: http://localhost:8000/health
- API文档: http://localhost:8000/docs
- 数据状态: http://localhost:8000/api/v1/data/status

### 4. 测试API

运行测试脚本：

```bash
python test_new_api.py
```

## 快速测试

### 使用curl测试

```bash
# 1. 获取系统状态
curl http://localhost:8000/api/v1/data/status
curl http://www.mcptools.xin:8000/api/v1/data/status


# 2. 获取股票列表
curl http://localhost:8000/api/v1/data/stock-list
curl http://www.mcptools.xin:8000/api/v1/data/stock-list


# 3. 获取历史K线（平安银行）
curl "http://localhost:8000/api/v1/data/kline?symbol=000001"
curl "http://www.mcptools.xin:8000/api/v1/data/kline?symbol=000001"


# 4. 获取实时分时数据
curl "http://localhost:8000/api/v1/data/kline/real?symbol=000001"
curl "http://www.mcptools.xin:8000/api/v1/data/kline/real?symbol=000001"


# 5. 获取资金流向
curl "http://localhost:8000/api/v1/data/fund-flow?symbol=000001"
curl "http://www.mcptools.xin:8000/api/v1/data/fund-flow?symbol=000001"

# 6. 获取盘口异动
curl "http://localhost:8000/api/v1/data/stock-changes?symbol=000001"
curl "http://www.mcptools.xin:8000/api/v1/data/stock-changes?symbol=000001"


```

### 使用Python测试

```python
import requests

# 获取历史K线
response = requests.get("http://localhost:8000/api/v1/data/kline?symbol=000001")
print(response.json())
```

## 常见问题

### Q1: 服务启动后没有数据？

**A**: 这是正常的。系统需要等待定时任务执行：
- 股票列表会在每周一9:00自动更新
- 实时数据只在交易时段（9:15-11:30, 13:00-15:00）更新
- 可以手动触发数据获取（见下方说明）

### Q2: 如何手动触发数据获取？

**A**: 可以直接调用数据管理器的方法：

```python
from app.services.stock_data_manager import get_stock_data_manager

manager = get_stock_data_manager()

# 获取股票列表
manager.fetch_stock_list()

# 获取单只股票的日K线
manager.fetch_daily_kline("000001")

# 获取实时数据
manager.fetch_realtime_data()

# 获取资金流向
manager.fetch_fund_flow()

# 获取盘口异动
manager.fetch_stock_changes()
```

### Q3: 数据存储在哪里？

**A**: 所有数据存储在 `data/` 目录下：
```
data/
├── stock_list/           # 股票列表
├── kline_daily/          # 历史日K线
├── kline_realtime/       # 实时分时数据
├── fund_flow/            # 资金流向
└── stock_changes/        # 盘口异动
```

### Q4: 如何清理旧数据？

**A**: 
- 实时数据可以定期清理（按日期目录删除）
- 历史K线自动保持最近90天
- 资金流向和盘口异动每次覆盖更新

### Q5: 如何修改数据获取频率？

**A**: 在 `app/core/config.py` 中修改配置：

```python
REALTIME_FETCH_INTERVAL: int = 60  # 实时数据获取间隔（秒）
FUND_FLOW_FETCH_INTERVAL: int = 300  # 资金流向获取间隔（秒）
STOCK_CHANGES_FETCH_INTERVAL: int = 300  # 盘口异动获取间隔（秒）
```

### Q6: 生产环境部署建议

**A**: 
1. 使用 `gunicorn` + `uvicorn` workers
2. 配置 nginx 反向代理
3. 设置系统服务自动启动
4. 配置日志轮转
5. 监控数据获取状态

示例启动命令：
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 日志查看

查看实时日志：

```bash
# 如果使用 uvicorn
tail -f logs/app.log

# 查看系统日志
journalctl -u aistock-server -f
```

## 性能监控

访问以下端点查看系统状态：

- `/health` - 健康检查
- `/api/v1/data/status` - 数据状态

## 下一步

- 阅读 `STOCK_DATA_API.md` 了解完整API文档
- 阅读 `IMPLEMENTATION_NOTES.md` 了解实现细节
- 根据需要调整配置参数
- 设置监控和告警

## 技术支持

如遇到问题，请查看：
1. 服务日志
2. `IMPLEMENTATION_NOTES.md` 文档
3. GitHub Issues
