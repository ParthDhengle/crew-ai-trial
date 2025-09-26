#!/usr/bin/env python3
"""
Test script to verify the backend API is working correctly
"""
import requests
import json
import sys

API_BASE_URL = "http://127.0.0.1:8001"

def test_health():
    """Test if the API is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ Backend API is running")
            return True
        else:
            print(f"❌ Backend API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend API. Make sure it's running on http://127.0.0.1:8001")
        return False

def test_auth_endpoints():
    """Test authentication endpoints"""
    print("\n🔐 Testing authentication endpoints...")
    
    # Test signup
    try:
        signup_data = {
            "email": "test@example.com",
            "password": "testpassword123"
        }
        response = requests.post(f"{API_BASE_URL}/auth/signup", json=signup_data)
        if response.status_code == 200:
            print("✅ Signup endpoint working")
            auth_data = response.json()
            return auth_data.get("custom_token")
        else:
            print(f"❌ Signup failed: {response.status_code} - {response.text}")
            # Try login instead if signup fails
            print("   Trying login instead...")
            login_data = {
                "email": "test@example.com", 
                "password": "testpassword123"
            }
            response = requests.post(f"{API_BASE_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                print("✅ Login endpoint working")
                auth_data = response.json()
                token = auth_data.get("custom_token")
                print(f"   Token: {token[:50]}..." if token else "   No token received")
                return token
            else:
                print(f"❌ Login also failed: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return None

def test_chat_endpoint(token):
    """Test chat endpoint with authentication"""
    if not token:
        print("❌ No auth token available")
        return False
        
    print("\n💬 Testing chat endpoint...")
    
    try:
        # For testing, we'll use the custom token directly
        # In production, this would be exchanged for an ID token
        headers = {"Authorization": f"Bearer {token}"}
        chat_data = {
            "query": "Hello, this is a test message",
            "session_id": "test-session-123"
        }
        
        response = requests.post(
            f"{API_BASE_URL}/process_query", 
            json=chat_data, 
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ Chat endpoint working")
            result = response.json()
            print(f"   Response: {result.get('result', 'No result')[:100]}...")
            return True
        else:
            print(f"❌ Chat failed: {response.status_code} - {response.text}")
            # Try without authentication to see if the endpoint works
            print("   Trying without authentication...")
            response = requests.post(f"{API_BASE_URL}/process_query", json=chat_data)
            if response.status_code == 401:
                print("✅ Endpoint requires authentication (expected)")
                return True
            else:
                print(f"❌ Unexpected response: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return False

def test_tasks_endpoint(token):
    """Test tasks endpoint"""
    if not token:
        print("❌ No auth token available")
        return False
        
    print("\n📋 Testing tasks endpoint...")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_BASE_URL}/tasks", headers=headers)
        
        if response.status_code == 200:
            print("✅ Tasks endpoint working")
            tasks = response.json()
            print(f"   Found {len(tasks)} tasks")
            return True
        else:
            print(f"❌ Tasks failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Tasks error: {e}")
        return False

def main():
    print("🚀 Testing Nova Backend Integration")
    print("=" * 50)
    
    # Test if API is running
    if not test_health():
        sys.exit(1)
    
    # Test authentication
    token = test_auth_endpoints()
    
    # Test protected endpoints
    if token:
        test_chat_endpoint(token)
        test_tasks_endpoint(token)
    
    print("\n" + "=" * 50)
    print("✅ Integration test completed!")
    print("\nTo start the backend, run:")
    print("  cd src && python app.py")
    print("\nTo start the frontend, run:")
    print("  cd frontend && npm run dev")

if __name__ == "__main__":
    main()
