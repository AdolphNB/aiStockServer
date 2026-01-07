from app.core.config import settings

def test_create_subscription(client):
    payload = {
        "machine_id": "test_machine_123",
        "plan_type": "1m"
    }
    response = client.post(f"{settings.API_V1_STR}/subscribe", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "expiry" in data
    assert len(data["token"]) > 0

def test_create_subscription_invalid_plan(client):
    payload = {
        "machine_id": "test_machine_123",
        "plan_type": "invalid_plan"
    }
    response = client.post(f"{settings.API_V1_STR}/subscribe", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid plan type"

def test_get_market_activity_no_token(client):
    response = client.get(f"{settings.API_V1_STR}/data/market-activity")
    # Depends on how fastapi handles missing required query param, usually 422
    assert response.status_code == 422

def test_get_market_activity_invalid_token(client):
    response = client.get(f"{settings.API_V1_STR}/data/market-activity?token=invalid_token")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"

def test_get_market_activity_valid_token(client):
    # 1. Create subscription to get a token
    payload = {
        "machine_id": "test_machine_456",
        "plan_type": "1m"
    }
    sub_response = client.post(f"{settings.API_V1_STR}/subscribe", json=payload)
    token = sub_response.json()["token"]
    
    # 2. Use token to get data
    response = client.get(f"{settings.API_V1_STR}/data/market-activity?token={token}")
    # It might return empty data or nulls, but should be 200 OK
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "data" in data
