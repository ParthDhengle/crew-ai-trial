#!/usr/bin/env python3
"""
Firebase Authentication Debug Script
Use this to test your Firebase setup and generate test tokens
"""

import os
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth

def test_firebase_setup():
    """Test Firebase initialization and create test tokens"""
    print("=== Firebase Auth Debug Script ===\n")
    
    # Load environment variables
    load_dotenv()
    
    # Check environment variables
    print("1. Checking environment variables...")
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    web_api_key = os.getenv("FIREBASE_WEB_API_KEY")
    
    print(f"   GOOGLE_APPLICATION_CREDENTIALS: {cred_path}")
    print(f"   FIREBASE_WEB_API_KEY: {web_api_key[:20]}..." if web_api_key else "   FIREBASE_WEB_API_KEY: Not set")
    
    if not cred_path:
        print("   ❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        return False
    
    if not os.path.exists(cred_path):
        print(f"   ❌ Credentials file not found: {cred_path}")
        return False
    
    if not web_api_key:
        print("   ❌ FIREBASE_WEB_API_KEY not set")
        return False
    
    print("   ✅ Environment variables OK\n")
    
    # Test Firebase initialization
    print("2. Testing Firebase initialization...")
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("   ✅ Firebase initialized successfully")
        else:
            print("   ✅ Firebase already initialized")
    except Exception as e:
        print(f"   ❌ Firebase initialization failed: {e}")
        return False
    
    print()
    
    # Test custom token creation
    print("3. Testing custom token creation...")
    test_uid = "test-user-123"
    try:
        custom_token = auth.create_custom_token(test_uid)
        if isinstance(custom_token, bytes):
            custom_token = custom_token.decode('utf-8')
        print(f"   ✅ Custom token created successfully")
        print(f"   Token preview: {custom_token[:50]}...")
        
        # Test token exchange
        print("\n4. Testing token exchange...")
        import requests
        
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={web_api_key}"
        body = {
            "token": custom_token,
            "returnSecureToken": True
        }
        
        response = requests.post(url, json=body, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            id_token = data.get("idToken")
            refresh_token = data.get("refreshToken")
            
            print("   ✅ Token exchange successful")
            print(f"   ID token preview: {id_token[:50]}..." if id_token else "   No ID token")
            print(f"   Refresh token preview: {refresh_token[:50]}..." if refresh_token else "   No refresh token")
            
            # Test ID token verification
            if id_token:
                print("\n5. Testing ID token verification...")
                try:
                    decoded_token = auth.verify_id_token(id_token)
                    verified_uid = decoded_token.get('uid')
                    print(f"   ✅ ID token verified successfully")
                    print(f"   Verified UID: {verified_uid}")
                    
                    if verified_uid == test_uid:
                        print("   ✅ UID matches original test UID")
                    else:
                        print(f"   ⚠️  UID mismatch: expected {test_uid}, got {verified_uid}")
                        
                except Exception as e:
                    print(f"   ❌ ID token verification failed: {e}")
                    return False
            
        else:
            error_data = response.json() if response.text else {}
            error_message = error_data.get("error", {}).get("message", "Unknown error")
            print(f"   ❌ Token exchange failed: {error_message}")
            print(f"   Status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Custom token creation failed: {e}")
        return False
    
    print("\n=== All tests passed! ===")
    print(f"\nFor testing your API endpoints, use this custom token:")
    print(f"{custom_token}")
    print(f"\nOr use this ID token:")
    print(f"{id_token}")
    
    return True

def create_test_user_token(uid: str):
    """Create a test token for a specific user"""
    try:
        custom_token = auth.create_custom_token(uid)
        if isinstance(custom_token, bytes):
            custom_token = custom_token.decode('utf-8')
        return custom_token
    except Exception as e:
        print(f"Error creating token for {uid}: {e}")
        return None

if __name__ == "__main__":
    success = test_firebase_setup()
    
    if success:
        print("\n=== Additional Test Tokens ===")
        test_uids = ["user1", "user2", "test-user"]
        
        for uid in test_uids:
            token = create_test_user_token(uid)
            if token:
                print(f"Token for {uid}: {token}")
    
    else:
        print("\n❌ Firebase setup has issues that need to be fixed.")
        print("\nCommon issues:")
        print("1. Check your Firebase credentials file path")
        print("2. Verify FIREBASE_WEB_API_KEY is correct")
        print("3. Ensure your Firebase project has Authentication enabled")
        print("4. Check that your service account has proper permissions")