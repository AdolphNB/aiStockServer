#!/usr/bin/env python3
"""
Test script to verify K-line API fix
Tests JSON serialization with various data types
"""
import requests
import json
import sys

BASE_URL = "http://www.mcptools.xin:8000"

def test_kline_api():
    """Test K-line API endpoint"""
    print("Testing K-line API...")
    print("-" * 50)
    
    try:
        url = f"{BASE_URL}/api/v1/data/kline?symbol=000001"
        print(f"Request: GET {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        if response.status_code == 200:
            # Try to parse JSON
            data = response.json()
            print(f"\nResponse structure:")
            print(f"  - code: {data.get('code')}")
            print(f"  - message: {data.get('message')}")
            
            if data.get('data'):
                result = data['data']
                print(f"  - columns: {len(result.get('columns', []))} columns")
                print(f"  - index: {len(result.get('index', []))} rows")
                print(f"  - data: {len(result.get('data', []))} rows")
                
                if result.get('columns'):
                    print(f"\nColumns: {result['columns']}")
                
                if result.get('data'):
                    print(f"\nFirst row sample:")
                    print(f"  {result['data'][0]}")
                    
                    print(f"\nLast row sample:")
                    print(f"  {result['data'][-1]}")
            
            print("\n✓ Test PASSED - JSON serialization successful")
            return True
        else:
            print(f"\n✗ Test FAILED - HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except json.JSONDecodeError as e:
        print(f"\n✗ Test FAILED - JSON decode error: {e}")
        print(f"Response text: {response.text[:500]}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Test FAILED - Request error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Test FAILED - Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_realtime_api():
    """Test realtime K-line API endpoint"""
    print("\n\nTesting Realtime K-line API...")
    print("-" * 50)
    
    try:
        url = f"{BASE_URL}/api/v1/data/kline/real?symbol=000001"
        print(f"Request: GET {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response code: {data.get('code')}")
            print(f"Message: {data.get('message')}")
            
            if data.get('data') and data['data'].get('data'):
                print(f"Rows: {len(data['data']['data'])}")
                print("\n✓ Test PASSED")
            else:
                print("\nℹ No data available (may be outside trading hours)")
            return True
        else:
            print(f"\n✗ Test FAILED - HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n✗ Test FAILED - Error: {e}")
        return False

def test_status_api():
    """Test status API endpoint"""
    print("\n\nTesting Status API...")
    print("-" * 50)
    
    try:
        url = f"{BASE_URL}/api/v1/data/status"
        print(f"Request: GET {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nSystem Status:")
            
            if data.get('data'):
                for key, value in data['data'].items():
                    print(f"  {key}: {value}")
            
            print("\n✓ Test PASSED")
            return True
        else:
            print(f"\n✗ Test FAILED - HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n✗ Test FAILED - Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("K-line API Fix Verification Test")
    print("=" * 50)
    
    results = []
    results.append(("K-line API", test_kline_api()))
    results.append(("Realtime API", test_realtime_api()))
    results.append(("Status API", test_status_api()))
    
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + ("=" * 50))
    if all_passed:
        print("All tests passed! 🎉")
        sys.exit(0)
    else:
        print("Some tests failed. Please check the logs.")
        sys.exit(1)
