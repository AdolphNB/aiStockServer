# Stock Data API 使用文档

## 概述

本API提供实时股票数据接口，包括历史K线、实时分时数据、资金流向和盘口异动等数据。

**访问地址**: `http://www.mcptools.xin:8000`

## 数据更新策略

### 运行时数据
- 所有数据优先存放在**内存**中，确保快速响应
- 收盘后自动备份到文件
- 服务启动时从文件加载历史数据到内存

### 定时任务
| 任务 | 执行时间 | 说明 |
|------|----------|------|
| 股票列表更新 | 每周一 9:00 | 更新 `ak.stock_info_a_code_name()` |
| 实时行情获取 | 开市时每1分钟 | 获取并分拆分时数据 |
| 资金流向获取 | 开市时每5分钟 | 覆盖更新资金流向数据 |
| 盘口异动获取 | 开市时每5分钟 | 覆盖更新盘口异动数据 |
| 数据备份 | 收盘后 15:30 | 将内存数据持久化到文件 |

### 开市时间
- 上午：9:15 - 11:30
- 下午：13:00 - 15:00
- 必需是交易日，同时在以上时间段，才启动定时读取

## API 接口

### 1. 历史 K 线数据获取

获取单只股票的历史日K线数据（最近90个交易日 + 当天）

**请求**
```
GET /api/v1/data/kline?symbol={stock_code}&include_today={true/false}
```

**参数**
- `symbol` (必需): 股票代码，例如 "000001"
- `include_today` (可选): 是否包含当天K线，默认 true

**返回示例**
```json
{
  "code": 200,
  "message": "Historical K-line data for 000001",
  "data": {
    "columns": ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅", "涨跌幅", "涨跌额", "换手率"],
    "index": [0, 1, 2, ...],
    "data": [
      ["2025-10-15", 10.5, 10.8, 11.0, 10.3, 1000000, 10800000, 0.67, 2.86, 0.3, 1.2],
      ["2025-10-16", 10.8, 11.2, 11.5, 10.6, 1200000, 13440000, 0.83, 3.70, 0.4, 1.4],
      ...
    ]
  }
}
```

### 2. 实时分时数据获取

获取股票当天的分时数据（1分钟线）

**请求**
```
GET /api/v1/data/kline/real?symbol={stock_code}
```

**参数**
- `symbol` (必需): 股票代码，例如 "000001"

**返回示例**
```json
{
  "code": 200,
  "message": "Realtime data for 000001",
  "data": {
    "columns": ["代码", "名称", "最新价", "涨跌幅", "涨跌额", "成交量", "成交额", "时间", ...],
    "index": [0, 1, 2, ...],
    "data": [
      ["000001", "平安银行", 10.85, 2.5, 0.27, 50000, 542500, "2026-01-19 09:31:00", ...],
      ["000001", "平安银行", 10.88, 2.8, 0.29, 52000, 565760, "2026-01-19 09:32:00", ...],
      ...
    ]
  }
}
```

### 3. 资金流向数据获取

获取个股即时资金流向数据

**请求**
```
GET /api/v1/data/fund-flow?symbol={stock_code}
```

**参数**
- `symbol` (可选): 股票代码。如果提供，返回该股票的数据；否则返回所有数据

**返回示例**
```json
{
  "code": 200,
  "message": "Fund flow data for 000001",
  "data": {
    "columns": ["代码", "名称", "最新价", "今日主力净流入-净额", "今日主力净流入-净占比", ...],
    "index": [0],
    "data": [
      ["000001", "平安银行", 10.85, 50000000, 5.2, ...]
    ]
  }
}
```

### 4. 盘口异动数据获取

获取盘口异动数据

**请求**
```
GET /api/v1/data/stock-changes?symbol={stock_code}
```

**参数**
- `symbol` (可选): 股票代码。如果提供，返回该股票的数据；否则返回所有数据

**返回示例**
```json
{
  "code": 200,
  "message": "Stock changes data for 000001",
  "data": {
    "columns": ["时间", "代码", "名称", "板块", "相关信息"],
    "index": [0, 1],
    "data": [
      ["14:55:51", "000001", "平安银行", "大笔买入", "124230,19.24000,0.300000"],
      ["14:50:43", "000001", "平安银行", "快速反弹", "296001,4.52000,0.280453"]
    ]
  }
}
```

### 5. 股票列表获取

获取所有A股股票列表

**请求**
```
GET /api/v1/data/stock-list
```

**返回示例**
```json
{
  "code": 200,
  "message": "Stock list",
  "data": {
    "columns": ["code", "name"],
    "index": [0, 1, 2, ...],
    "data": [
      ["000001", "平安银行"],
      ["000002", "万科A"],
      ["000004", "国华网安"],
      ...
    ]
  }
}
```

### 6. 系统状态查询

获取系统数据状态信息

**请求**
```
GET /api/v1/data/status
```

**返回示例**
```json
{
  "code": 200,
  "message": "System status",
  "data": {
    "stock_list": {
      "count": 5474,
      "last_updated": "2026-01-19T09:00:00"
    },
    "kline_daily": {
      "count": 100,
      "stocks": ["000001", "000002", "000004", ...]
    },
    "kline_realtime": {
      "count": 5474,
      "last_updated": "2026-01-19T14:55:00"
    },
    "fund_flow": {
      "count": 5474,
      "last_updated": "2026-01-19T14:55:00"
    },
    "stock_changes": {
      "count": 3174,
      "last_updated": "2026-01-19T14:55:00"
    }
  }
}
```

## 错误码

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 404 | 未找到数据 |
| 500 | 服务器错误 |

## 使用示例

### Python 示例

```python
import requests
import pandas as pd

# 获取历史K线数据
response = requests.get("http://www.mcptools.xin:8000/api/v1/data/kline?symbol=000001")
data = response.json()

if data['code'] == 200:
    # 转换为 DataFrame
    df = pd.DataFrame(
        data['data']['data'],
        columns=data['data']['columns']
    )
    print(df.tail())
```

### JavaScript 示例

```javascript
// 获取实时分时数据
fetch('http://www.mcptools.xin:8000/api/v1/data/kline/real?symbol=000001')
  .then(response => response.json())
  .then(data => {
    if (data.code === 200) {
      console.log('Columns:', data.data.columns);
      console.log('Data:', data.data.data);
    }
  });
```

## 性能优化

1. **内存优先**: 所有数据存储在内存中，确保毫秒级响应
2. **并发控制**: 使用线程锁保证数据一致性
3. **防重复获取**: 实时数据获取时检查是否有任务正在执行
4. **定时备份**: 收盘后自动备份，不影响交易时段性能

## 数据目录结构

```
data/
├── stock_list/           # 股票列表数据
│   └── stock_info_a_code_name.csv
├── kline_daily/          # 历史日K线数据（按股票代码命名）
│   ├── 000001.csv
│   ├── 000002.csv
│   └── ...
├── kline_realtime/       # 当日分时数据
│   ├── 000001.csv
│   ├── 000002.csv
│   └── ...
├── fund_flow/            # 资金流向数据
│   └── fund_flow_latest.csv
└── stock_changes/        # 盘口异动数据
    └── stock_changes_latest.csv
```

## 注意事项

1. 所有时间均为东八区（北京时间）
2. 数据仅在交易日和交易时段更新
3. 历史K线数据默认返回前复权（qfq）数据
4. 实时数据延迟约1分钟（受限于数据源更新频率）
5. 资金流向和盘口异动数据每5分钟更新一次

## 技术支持

如有问题，请访问项目GitHub仓库或联系技术支持。
