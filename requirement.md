# AIStock Remote Server Requirements & Technical Specification

## 1. Project Overview

Build a remote server on Ubuntu to act as a centralized data hub and subscription management system for the AIStock PC Client.
**Domain**: `http://www.mcptools.xin`
**Admin**: `http://www.mcptools.xin/admin`

## 2. Technical Architecture

### 2.1 Technology Stack

- **Language**: Python 3.10+
- **Web Framework**: FastAPI (High performance, async support)
- **Data Source**: `akshare` (Stock data)
- **Task Scheduler**: `APScheduler` (Async scheduling for trading hours)
- **Database**: SQLite (MVP) / PostgreSQL (Production) - using `SQLAlchemy` ORM.
- **Cache**: In-Memory (Global Python Dictionary or `cachetools`) for real-time stock data.
- **Server**: Uvicorn / Gunicorn
- **Deployment**: Docker Compose

### 2.2 System Modules

#### A. Data Fetcher Module (Background Service)

- **Responsibility**: Fetch stock market activity and money flow data.
- **Schedule**:
  - Trading Days Only (Monday-Friday, excluding holidays - need a holiday calendar logic).
  - Time Windows: 09:30-11:30, 13:00-15:00.
  - Interval: Configurable (e.g., every 60 seconds).
- **Storage**:
  - Store latest data in **RAM** (In-Memory) for O(1) access.
  - Optional: Persist history to DB for analysis (if needed later).
- **Target Data**:
  - `ak.stock_market_activity_legu()` (赚钱效应)
  - Other money flow interfaces as needed.

#### B. Subscription & Payment Module

- **Plans**: 1 Month, 3 Months, 6 Months, 12 Months.
- **Workflow**:
  1. Client requests subscription -> Server generates Order ID.
  2. Client shows Payment QR (Mock or Integration? _Assumed Mock/Manual verification for now based on "popup QR code" description_).
  3. Payment Confirmed -> Server updates DB, generates **Auth Token**.
  4. Token is sent to Client.
- **Token**: Long-lived API Key or JWT. Used for verifying client data requests.

#### C. API Service (REST Client Interface)

- **Auth**: Bearer Token or Query Param `?token=...`.
- **Concurrency**: Asyncio based to support 20+ concurrent users easily.
- **Endpoints**:
  - `POST /api/v1/subscribe`: Create subscription order.
  - `GET /api/v1/data/market-activity`: Get in-memory cached market data (Requires Token).
  - `GET /api/v1/status`: Server health check.

#### D. Admin Dashboard

- **Access**: Web Browser (`/admin`).
- **Auth**: Basic Auth or dedicated Admin Login.
- **Features**:
  - View all subscriptions.
  - Add/Modify/Delete subscriptions (Manual activation support).
  - View Server Status (Memory cache status).

## 3. Data Models (Draft)

### User / Subscription

```python
class Subscription(Base):
    id = Column(Integer, primary_key=True)
    machine_id = Column(String, index=True) # ID of the PC Client
    token = Column(String, unique=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    plan_type = Column(String) # "1m", "3m", "6m", "12m"
    is_active = Column(Boolean, default=True)
```

## 4. Interfaces & Implementation Details

### 4.1 Data Interface Example

```python
# GET /api/v1/data/market-activity
# Header: Authorization: Bearer <TOKEN>
{
    "timestamp": "2026-01-07 14:30:00",
    "data": {
        "stats": [...], # from akshare
        "limit_up_count": 50,
        "limit_down_count": 2
    }
}
```

### 4.2 Load Balancing

- For 20 users, a single FastAPI process is sufficient.
- For 1000+ users, use Nginx Load Balancer upstream to multiple Docker containers.
- **Requirement**: Design "Stateless" API where possible. Data Fetcher should be a singleton or use a shared Redis cache if scaled (currently RAM is fine for single node).

## 5. Next Steps

1. Setup RemoteServer project in `d:\mcpServer\aiStock\remoteServer`.
2. Implement Data Fetcher with `akshare`.
3. Implement FastAPI skeleton.
