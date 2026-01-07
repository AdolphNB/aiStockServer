# AIStock Server Testing Guide

This document provides instructions on how to test the AIStock Server, both using the automated test suite and manually via the interactive API documentation.

## 1. Environment Setup

Before testing, ensure your environment is set up and dependencies are installed.

```bash
# Install dependencies
uv sync
# OR if using pip directly
pip install -r requirements.txt
```

## 2. Automated Testing

The project includes a comprehensive test suite using `pytest`. This is the recommended way to verify the core functionality.

### Running Tests

Execute the following command in the project root:

```bash
uv run pytest
```

### What is tested?

- **Health Check**: Verifies the server is running.
- **Subscriptions**: Tests creating subscriptions (valid and invalid plans).
- **Market Data**: Tests access control for market data (valid, invalid, and missing tokens).

## 3. Manual Testing (Interactive)

FastAPI provides an automatic interactive API documentation interface (Swagger UI) that makes manual testing very easy.

### Step 1: Start the Server

Run the server locally:

```bash
uv run python app/main.py
```

_The server will start at `http://0.0.0.0:8000`_

### Step 2: Access Swagger UI

Open your web browser and navigate to:
**http://localhost:8000/docs**

### Step 3: Execute Test Scenarios

#### Scenario A: Health Check

1. Click on **`GET /`**.
2. Click **Try it out** -> **Execute**.
3. **Verify**: Response body is `{"message": "AIStock Remote Server is Running"}`.

#### Scenario B: Create a Subscription

1. Click on **`POST /api/v1/subscribe`**.
2. Click **Try it out**.
3. Edit the Request body:
   ```json
   {
     "machine_id": "my-test-machine",
     "plan_type": "1m"
   }
   ```
4. Click **Execute**.
5. **Verify**: Response code is `200`. Copy the `token` string from the response for the next step.

#### Scenario C: Access Market Data

1. Click on **`GET /api/v1/data/market-activity`**.
2. Click **Try it out**.
3. Paste the `token` you copied into the `token` field.
4. Click **Execute**.
5. **Verify**:
   - If the scheduler has run, you will see data.
   - If effective immediately, response code should be `200`.

## 4. Troubleshooting

- **"Event loop is closed"**: This might happen if `pytest-asyncio` conflicts. Ensure you are using the provided configuration.
- **Database Errors**: The automated tests use an in-memory database. For manual testing, a local `aistock.db` file will be created. You can delete this file to reset the data.
