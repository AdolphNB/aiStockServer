# 实时行情与K线生成重构方案

## 1. 场景分析

**需求**: 每分钟调用 `ak.stock_zh_a_spot_em()` 获取全市场 (~5000 只) 股票的快照数据，并将其转化为各股票的 **1分钟 K线数据**，供 API `/data/kline/real` 查询。

**当前挑战**:

1.  **I/O 瓶颈**: 如果按照传统方式，每分钟通过循环打开 5000 个 CSV 文件并追加数据，文件系统的开销（open/write/close）将极其巨大，导致处理延迟远超 1 分钟。
2.  **数据冗余**: `spot_em` 接口返回的是全市场快照，其中包含很多不变的数据（如名称），每分钟重复存储造成浪费。
3.  **并发读写冲突**: 写入进程在写文件的同时，API 进程可能正在读取，容易导致文件锁或数据不一致。
4.  **稳定性问题**: 原有方案在运行几次后容易中断，通常由网络超时或 I/O 阻塞导致。

## 2. 核心设计：内存化与批量写入

鉴于数据的时效性（"实时" K线通常只关注**当天**的数据，历史数据可以归档），我们推荐 **Redis** 或 **SQLite (WAL模式)** 作为核心存储引擎。

### 方案 A：Redis 方案 (高性能，推荐)

利用 Redis 的内存读写速度，完全避免磁盘 I/O 瓶颈。

- **数据结构设计**:
  - **实时快照 (Latest)**: 哈希表 `HSET quote:latest {stock_code} {json_data}`
    - 用途：提供 "最新价"、"涨跌幅" 等看板数据。
    - 更新：Pipelining 批量更新 5000 个 Key，耗时 < 100ms。
  - **今日分钟线 (Intraday Series)**: 列表 `RPUSH kline:1m:{date}:{stock_code} {json_data}`
    - 用途：`/data/kline/real` 接口。
    - 数据：存储紧凑的 JSON 或 MessagePack 字符串 `[time, open, high, low, close, vol]`。
    - 过期：设置 24小时 TTL，每日自动清理。

- **流程**:
  1.  **Fetcher**: 获取 DF -> 转换为 List of Dict -> Redis Pipeline 批量 RPUSH。
  2.  **API**: `GET /data/kline/real?code=000001` -> `LRANGE kline:1m:{date}:000001 0 -1` -> Return。

### 方案 B：SQLite (WAL) 方案 (单机部署友好)

如果不想部署 Redis，SQLite 的 WAL (Write-Ahead Logging) 模式在单文件写入性能上非常优秀，且支持高并发读。

- **表结构**:

  ```sql
  CREATE TABLE IF NOT EXISTS intraday_kline (
      date TEXT, -- YYYY-MM-DD
      time TEXT, -- HH:MM
      code TEXT,
      open REAL,
      high REAL,
      low REAL,
      close REAL,
      volume INTEGER,
      PRIMARY KEY (date, code, time)
  );
  CREATE INDEX idx_query ON intraday_kline (date, code);
  ```

- **流程**:
  1.  **Fetcher**: 获取 DF -> Pandas 处理 -> `df.to_sql(chunksize=5000, method='multi')` (批量插入)。
      - _关键点_: 开启 `PRAGMA journal_mode=WAL;` 和 `PRAGMA synchronous=NORMAL;`。
  2.  **API**: `SELECT * FROM intraday_kline WHERE code=? AND date=? ORDER BY time`.

## 3. 具体重构代码逻辑 (伪代码)

鉴于您使用 Python，推荐 **SQLite 方案** 作为起步（无需安装 Redis 服务），如果性能不足再切换 Redis。

### 3.1 Fetcher (数据获取层)

```python
# services/fetcher.py
import akshare as ak
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine

# 使用 SQLite，开启 WAL 模式以支持并发读写
engine = create_engine("sqlite:///data/realtime.db?check_same_thread=False")
engine.execute("PRAGMA journal_mode=WAL")

def fetch_and_store_realtime():
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")

    # 1. 获取全量数据 (约 0.5s - 2s)
    df = ak.stock_zh_a_spot_em()

    # 2. 数据清洗与转化 (Vectorized operation, < 100ms)
    # 假设 df 列名为 '代码', '最新价' 等
    # 对于 1分钟线，Snapshot 的 Close 即为当前的 Price
    # 真实场景可能需要聚合 Tick，但此处简化为 Snap=KLine
    kline_df = pd.DataFrame()
    kline_df['code'] = df['代码']
    kline_df['date'] = today
    kline_df['time'] = current_time
    kline_df['open'] = df['最新价'] # 简化处理：全等于最新价
    kline_df['high'] = df['最新价']
    kline_df['low'] = df['最新价']
    kline_df['close'] = df['最新价']
    kline_df['volume'] = df['成交量']

    # 3. 批量写入 DB (Single Transaction, < 200ms)
    with engine.begin() as conn:
        kline_df.to_sql('intraday_kline', conn, if_exists='append', index=False)

    print(f"Stored {len(kline_df)} records for {current_time}")
```

### 3.2 API (服务层)

```python
# api/endpoints/data.py
from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()

@router.get("/kline/real")
async def get_realtime_kline(code: str):
    # 直接查询 SQLite，非常快
    # 结合 SQLAlchemy Async 或 databases 库可实现异步非阻塞
    query = text("SELECT time, open, high, low, close, volume FROM intraday_kline WHERE code=:code AND date=DATE('now')")

    # ... 执行查询并返回 ...
    # 下方第5节将介绍具体的返回格式代码
    pass
```

## 4. 总结架构优势

1.  **极速 I/O**: `df.to_sql` 批量写入 5000 行 SQLite 仅需几十毫秒，完全解决了 5000 个文件打开关闭的耗时问题。
2.  **查询高效**: 基于 B-Tree 索引的查询（`WHERE code='000001'`）是 $O(\log N)$ 复杂度，毫秒级响应。
3.  **零文件碎片**: 所有临时数据在一个 `.db` 文件中，文件系统更干净。

## 5. API 响应格式方案 (DataFrame 直传)

为了满足客户端**免转换直接使用 DataFrame**的需求，推荐使用 **Apache Arrow** 或 **Parquet** 序列化协议。相比 JSON，它们支持类型保留（int 还是 int），且支持 "Zero-Copy" 反序列化。

### 方案 A: Apache Arrow (Feather) - _推荐_

速度最快，专为 DataFrame 内存交换设计。

**Server 端 (FastAPI):**

```python
import polars as pl # 或者 pandas
from fastapi import Response
import io

@router.get("/kline/real/arrow")
async def get_kline_arrow(code: str):
    # 1. Fetch data from DB
    query = f"SELECT time, open, high, low, close, volume FROM intraday_kline WHERE code='{code}'"
    df = pd.read_sql(query, engine) # 或者使用 connectorx 加速

    # 2. Serialize to Arrow IPC Stream
    # pandas
    sink = io.BytesIO()
    df.to_feather(sink) # 使用 Feather 格式 (Arrow IPC)
    sink.seek(0)

    return Response(
        content=sink.getvalue(),
        media_type="application/vnd.apache.arrow.file" # 或 application/octet-stream
    )
```

**Client 端 (Python):**

```python
import pandas as pd
import requests
import io

def get_kline_df(code):
    url = f"http://server/api/v1/data/kline/real/arrow?code={code}"
    resp = requests.get(url)

    # 一行代码直接还原为 DataFrame，保留数据类型
    df = pd.read_feather(io.BytesIO(resp.content))
    return df
```

### 方案 B: Parquet

兼容性更好，压缩率高，适合网络带宽受限场景。

**Server 端:**

```python
    # ...
    sink = io.BytesIO()
    df.to_parquet(sink)
    return Response(
        content=sink.getvalue(),
        media_type="application/octet-stream"
    )
```

**Client 端:**

```python
    df = pd.read_parquet(io.BytesIO(resp.content))
```

### 为什么不推荐 Pickle?

虽然 `pd.read_pickle` 最方便，但 Pickle 存在严重的安全风险（可执行任意代码）。除非您的 Server 和 Client 完全可信且在内网，否则严禁在 API 中使用 Pickle。

## 6. 稳定性保障设计 (彻底解决中断问题)

为了彻底解决 **"运行一两次后中断/停止"** 的问题，我们必须放弃 "API 进程内线程" 的做法，改用 **独立守护进程**。

### 6.1 核心原则

1.  **独立进程 (Independent Process)**: Fetcher 必须是独立的 `python run_fetcher.py` 进程，不依赖 API Server。即使 API Server 重启，Fetcher 也不受影响。
2.  **死循环模式 (While True Loop)**: 放弃复杂的 `APScheduler` 或 `Celery` 定时器（它们在异常时容易静默失败），改用最简单粗暴的 `while True` + `sleep`，这是最难 "死掉" 的结构。
3.  **全局异常捕获 (Pokemon Exception Handling)**: 必须捕获 `Exception` (所有异常)，打印错误日志，然后 `continue`。绝不能让单个网络超时导致进程退出。
4.  **网络超时控制**: `akshare` 底层使用 `requests`，如果网络卡死可能无限等待。必须强行设置超时。

### 6.2 推荐实现代码 (Robust Looper)

```python
# run_fetcher.py
import time
import logging
import traceback
from datetime import datetime
from func_timeout import func_timeout, FunctionTimedOut # 需要 pip install func-timeout

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fetcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Fetcher")

def job():
    """单次抓取任务"""
    logger.info("Starting fetch cycle...")
    # call your fetch logic here
    fetch_and_store_realtime()
    logger.info("Fetch cycle completed.")

def main():
    logger.info("Fetcher process started.")

    while True:
        try:
            start_time = time.time()

            # 使用 func_timeout 强制限制单次运行时间
            # 用户反馈需大于100s，这里设置为 120秒
            try:
                func_timeout(120, job)
            except FunctionTimedOut:
                logger.error("Job timed out! Akshare might be hanging.")
            except Exception as e:
                logger.error(f"Job failed with error: {e}")
                logger.error(traceback.format_exc())

            # 计算需要休眠的时间，保证整分钟对齐 (可选)
            # 或简单 sleep 60秒
            elapsed = time.time() - start_time
            sleep_time = max(0, 60 - elapsed)

            time.sleep(sleep_time)

        except Exception as e:
            # 外层捕获，防止 while 循环崩溃 (极罕见情况)
            logger.critical(f"Critical Loop Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
```

### 6.3 部署建议

在 Linux/Windows Server 上，建议使用 **Supervisor** 或 **Systemd** 来管理这个进程。如果它真的崩溃退出了，操作系统会自动重启它。

**Windows下简单保活脚本 (`start_fetcher.bat`)**:

```bat
:loop
python run_fetcher.py
echo Fetcher crashed, restarting in 5 seconds...
timeout /t 5
goto loop
```
