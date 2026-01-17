"""
Quick test script for aiStockServer realtime stock data functionality
"""
import requests
import json
import time

# 默认使用阿里云服务器地址
# 如果要测试本地服务器，改为 "http://localhost:8000"
SERVER_URL = "http://www.mcptools.xin:8000"

def test_watch_stocks():
    """Test updating watched stocks"""
    print("=== Testing Watch Stocks API ===")
    
    stock_codes = ["000001", "600519", "300750"]
    response = requests.post(
        f"{SERVER_URL}/api/client/data/watch-stocks",
        json={"stock_codes": stock_codes}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_realtime_stocks():
    """Test fetching realtime stock data"""
    print("=== Testing Realtime Stocks API ===")
    
    # Wait a bit for server to fetch data
    print("Waiting 5 seconds for server to fetch data...")
    time.sleep(5)
    
    stock_codes = ["000001", "600519", "300750"]
    response = requests.post(
        f"{SERVER_URL}/api/client/data/realtime-stocks",
        json={"stock_codes": stock_codes}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Timestamp: {data.get('timestamp')}")
    print(f"Number of stocks: {len(data.get('data', {}))}")
    
    for code, info in data.get('data', {}).items():
        print(f"\n{code} - {info.get('name')}:")
        print(f"  Price: {info.get('price')}")
        print(f"  Change: {info.get('change_percent')}%")
        print(f"  Volume Ratio: {info.get('volume_ratio')}")
        print(f"  Turnover Rate: {info.get('turnover_rate')}%")
    print()

def test_kline_data():
    """Test fetching K-line data"""
    print("=== Testing K-line Data API ===")
    
    stock_code = "000001"
    response = requests.get(
        f"{SERVER_URL}/api/client/data/kline/{stock_code}",
        params={
            "period": "daily",
            "adjust": "qfq",
            "days": 10
        }
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Stock Code: {data.get('stock_code')}")
    print(f"Number of K-line records: {len(data.get('data', []))}")
    
    if data.get('data'):
        print("\nFirst record:")
        first = data['data'][0]
        print(f"  Date: {first.get('date')}")
        print(f"  Open: {first.get('open')}, Close: {first.get('close')}")
        print(f"  High: {first.get('high')}, Low: {first.get('low')}")
        print(f"  Volume: {first.get('volume')}")
        
        print("\nLast record:")
        last = data['data'][-1]
        print(f"  Date: {last.get('date')}")
        print(f"  Open: {last.get('open')}, Close: {last.get('close')}")
        print(f"  High: {last.get('high')}, Low: {last.get('low')}")
        print(f"  Volume: {last.get('volume')}")
    print()

def main():
    print("Starting aiStockServer API Tests")
    print(f"Server URL: {SERVER_URL}\n")
    
    try:
        # Test 1: Update watched stocks
        test_watch_stocks()
        
        # Test 2: Fetch realtime stock data
        test_realtime_stocks()
        
        # Test 3: Fetch K-line data
        test_kline_data()
        
        print("=== All Tests Completed ===")
        
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to server at {SERVER_URL}")
        print("Please make sure the server is running:")
        print("  cd aiStockServer")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
