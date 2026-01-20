# 股票数据服务器重构方案：高性能多进程 & CSV 透传架构

## 1. 架构思想与核心理念

### 1.1 生产者-消费者解耦 (Producer-Consumer Decoupling)
将系统拆分为两个独立的进程，通过物理隔离彻底解决 Python GIL（全局解释器锁）导致的并发瓶颈：
*   **生产者进程 (Fetcher Engine)**：专职负责与 `akshare` 交互、数据清洗及写入缓存。
*   **消费者进程 (API Server)**：专职负责响应 HTTP 请求，通过读取缓存数据并透传给客户端。

### 1.2 零拷贝与 CSV 直接透传 (Zero-Copy CSV Transmission)
放弃传统的 `DataFrame -> JSON -> HTTP` 转换模式，改用 `DataFrame -> CSV -> FileResponse`：
*   **服务端零负载**：API 进程不进行数据解析和序列化，仅进行文件流转发。
*   **传输高效**：CSV 格式相比 JSON 冗余更少，配合 Gzip 压缩可达到极高的传输效率。
*   **客户端友好**：客户端可直接使用 `pandas.read_csv(url)` 获取数据，无缝对接金融分析流程。

### 1.3 共享内存盘交互 (RAM Disk IPC)
*   **存储介质**：利用虚拟内存盘 (RAM Disk) 或高性能 NVMe SSD 作为共享缓存目录。
*   **原子切换**：生产者写入 `.tmp` 后缀的临时文件，完成后通过 `os.replace()` 原子重命名为正式文件，确保读取者永远不会拿到“写了一半”的数据。

---

## 2. 技术细节

### 2.1 存储结构 (Cache Layout)
```text
shared_cache/
├── realtime/               # 实时分时数据 (1分钟线)
│   ├── 000001.csv
│   └── 600519.csv
├── market_snap/            # 全市场快照
│   └── latest_spot.csv
├── fund_flow/              # 资金流向
│   └── latest_flow.csv
└── stock_changes/          # 盘口异动
    └── latest_changes.csv
```

### 2.2 核心逻辑实现
*   **原子写入 (Fetcher)**:
    ```python
    df.to_csv("path/to/data.csv.tmp", index=False)
    os.replace("path/to/data.csv.tmp", "path/to/data.csv")
    ```
*   **极速透传 (FastAPI)**:
    ```python
    @app.get("/api/v1/data/...")
    async def get_data():
        return FileResponse("path/to/data.csv", media_type="text/csv")
    ```

---

## 3. 实现步骤

### 第一阶段：基础设施与环境准备
1.  **创建缓存目录**：在项目根目录创建 `shared_cache/` 及其子目录。
2.  **依赖安装**：确保环境中有 `pyarrow` (虽然用CSV，但保留高效处理能力)。
3.  **配置更新**：在 `settings.py` 中增加 `CACHE_DIR` 配置，指向 `shared_cache/`。

### 第二阶段：开发生产者进程 (Fetcher Engine)
1.  **模块解耦**：从原 `scheduler.py` 迁移逻辑，创建 `app/services/fetcher_engine.py`。
2.  **任务改造**：
    *   修改定时任务，将抓取到的 `DataFrame` 直接写入对应的 `shared_cache/` CSV 文件。
    *   实现“原子重命名”逻辑。
3.  **独立运行能力**：确保该模块可以作为一个独立的脚本运行。

### 第三阶段：重构消费者进程 (API Server)
1.  **接口重写**：修改 `app/api/endpoints/data.py` 中的所有数据查询接口。
2.  **数据融合策略**：为了保持 API 进程的“零计算”，对于“历史 K 线 + 当日实时”这种复合需求，由 **Fetcher 进程** 负责预先合并成一个 `full_kline_{symbol}.csv` 文件，API 进程仅负责下发。
3.  **移除复杂逻辑**：删除 API 进程中原有的 `dataframe_to_json_response` 及复杂的内存合并逻辑。
4.  **实现 FileResponse**：将接口统一修改为返回 CSV 文件的 `FileResponse` 模式。

### 第四阶段：开发系统编排器 (run_server.py)
1.  **多进程管理**：使用 `multiprocessing.Process` 同时启动 Fetcher 和 API 进程。
2.  **一键启动**：编写 `run_server.py` 作为主入口。
3.  **优雅退出 (Cleanup)**：
    *   捕获 `Ctrl+C` (SIGINT)。
    *   依次关闭子进程。
    *   **自动清理**：退出前删除 `shared_cache/` 下的所有 `.csv` 和 `.tmp` 文件，确保存储环境整洁。

### 第五阶段：测试与验证
1.  **性能压测**：对比重构前后 API 在高频数据抓取时的响应延迟。
2.  **客户端兼容性测试**：编写简单的 Python 脚本，验证 `pd.read_csv(url)` 是否能正确解析返回的 CSV 流。

---

## 4. 预期收益
*   **稳定性**：Fetcher 进程的网络波动或计算卡顿完全不影响 API 响应。
*   **吞吐量**：API 层的并发支撑能力预计提升 5-10 倍。
*   **运维简易度**：一键启停，且缓存文件随用随清，不占用持久化磁盘空间。
