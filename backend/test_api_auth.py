"""Test API authentication endpoints directly"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_signup_api():
    """Test signup API endpoint"""
    print("=" * 60)
    print("🧪 Testing Signup API Endpoint")
    print("=" * 60)
    
    # Generate unique email
    timestamp = int(datetime.now().timestamp())
    test_user = {
        "name": "API Test User",
        "email": f"apitest{timestamp}@savitara.com",
        "password": "SecurePass123!",
        "role": "grihasta"
    }
    
    print(f"\n📝 Registering new user:")
    print(f"   Email: {test_user['email']}")
    print(f"   Name: {test_user['name']}")
    print(f"   Role: {test_user['role']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json=test_user,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Signup successful!")
            print(f"   User ID: {data.get('user', {}).get('id')}")
            print(f"   Email: {data.get('user', {}).get('email')}")
            print(f"   Role: {data.get('user', {}).get('role')}")
            print(f"   Access Token: {data.get('access_token', '')[:50]}...")
            print(f"   Refresh Token: {data.get('refresh_token', '')[:50]}...")
            return test_user
        else:
            print(f"❌ Signup failed!")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def test_login_api(credentials):
    """Test login API endpoint"""
    print("\n" + "=" * 60)
    print("🔑 Testing Login API Endpoint")
    print("=" * 60)
    
    print(f"\n📝 Logging in:")
    print(f"   Email: {credentials['email']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={
                "email": credentials["email"],
                "password": credentials["password"]
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(f"   User ID: {data.get('user', {}).get('id')}")
            print(f"   Email: {data.get('user', {}).get('email')}")
            print(f"   Role: {data.get('user', {}).get('role')}")
            print(f"   Access Token: {data.get('access_token', '')[:50]}...")
            print(f"   Refresh Token: {data.get('refresh_token', '')[:50]}...")
            return data
        else:
            print(f"❌ Login failed!")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def test_me_endpoint(access_token):
    """Test /me endpoint with access token"""
    print("\n" + "=" * 60)
    print("👤 Testing /me Endpoint (Protected)")
    print("=" * 60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Profile retrieved successfully!")
            print(f"   User ID: {data.get('id')}")
            print(f"   Email: {data.get('email')}")
            print(f"   Name: {data.get('name')}")
            print(f"   Role: {data.get('role')}")
            print(f"   Status: {data.get('status')}")
            return data
        else:
            print(f"❌ Profile retrieval failed!")
            print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None

if __name__ == "__main__":
    print("\n🚀 Starting API Authentication Tests\n")
    
    # Test signup
    user_credentials = test_signup_api()
    
    if user_credentials:
        # Test login
        login_result = test_login_api(user_credentials)
        
        if login_result:
            # Test protected endpoint
            access_token = login_result.get("access_token")
            if access_token:
                test_me_endpoint(access_token)
    
    print("\n" + "=" * 60)
    print("🎉 API Tests Complete!")
    print("=" * 60)
