"""
Test script for new stock data API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"


def test_data_status():
    """Test data status endpoint"""
    print("\n=== Testing Data Status ===")
    response = requests.get(f"{BASE_URL}/data/status")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_stock_list():
    """Test stock list endpoint"""
    print("\n=== Testing Stock List ===")
    response = requests.get(f"{BASE_URL}/data/stock-list")
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Code: {data['code']}")
    print(f"Message: {data['message']}")
    if data['data']:
        print(f"Columns: {data['data']['columns']}")
        print(f"Total stocks: {len(data['data']['data'])}")
        print(f"First 3 stocks: {data['data']['data'][:3]}")


def test_historical_kline(symbol="000001"):
    """Test historical K-line endpoint"""
    print(f"\n=== Testing Historical K-line for {symbol} ===")
    response = requests.get(f"{BASE_URL}/data/kline?symbol={symbol}")
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Code: {data['code']}")
    print(f"Message: {data['message']}")
    if data['data']:
        print(f"Columns: {data['data']['columns']}")
        print(f"Total records: {len(data['data']['data'])}")
        print(f"Last 3 records:")
        for record in data['data']['data'][-3:]:
            print(f"  {record}")


def test_realtime_kline(symbol="000001"):
    """Test realtime K-line endpoint"""
    print(f"\n=== Testing Realtime K-line for {symbol} ===")
    response = requests.get(f"{BASE_URL}/data/kline/real?symbol={symbol}")
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Code: {data['code']}")
    print(f"Message: {data['message']}")
    if data['data']:
        print(f"Columns: {data['data']['columns']}")
        print(f"Total records: {len(data['data']['data'])}")
        if len(data['data']['data']) > 0:
            print(f"Last 3 records:")
            for record in data['data']['data'][-3:]:
                print(f"  {record[:5]}...")  # Show first 5 fields


def test_fund_flow(symbol="000001"):
    """Test fund flow endpoint"""
    print(f"\n=== Testing Fund Flow for {symbol} ===")
    response = requests.get(f"{BASE_URL}/data/fund-flow?symbol={symbol}")
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Code: {data['code']}")
    print(f"Message: {data['message']}")
    if data['data']:
        print(f"Columns: {data['data']['columns']}")
        print(f"Total records: {len(data['data']['data'])}")


def test_stock_changes(symbol="000001"):
    """Test stock changes endpoint"""
    print(f"\n=== Testing Stock Changes for {symbol} ===")
    response = requests.get(f"{BASE_URL}/data/stock-changes?symbol={symbol}")
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Code: {data['code']}")
    print(f"Message: {data['message']}")
    if data['data']:
        print(f"Columns: {data['data']['columns']}")
        print(f"Total records: {len(data['data']['data'])}")


if __name__ == "__main__":
    try:
        print("=" * 60)
        print("Testing New Stock Data API Endpoints")
        print("=" * 60)
        
        # Test all endpoints
        test_data_status()
        test_stock_list()
        test_historical_kline("000001")
        test_realtime_kline("000001")
        test_fund_flow("000001")
        test_stock_changes("000001")
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to server.")
        print("Please make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"\nError during testing: {e}")
