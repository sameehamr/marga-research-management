#!/usr/bin/env python3
"""
Test login via HTTP POST to simulate browser login
"""
import requests
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_web_login():
    """Test login via HTTP request"""
    base_url = "http://127.0.0.1:5000"
    
    try:
        # First, check if the server is running
        print("🌐 Testing web server connection...")
        response = requests.get(base_url, timeout=5)
        print(f"✅ Server is running! Status: {response.status_code}")
        
        # Test login form submission
        print("\n🔐 Testing login form submission...")
        
        session = requests.Session()
        
        # Get the login page first to establish session
        login_page = session.get(f"{base_url}/login", timeout=5)
        print(f"Login page status: {login_page.status_code}")
        
        # Submit login credentials
        login_data = {
            'username': 'manager',
            'password': 'manager123'
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data, timeout=5, allow_redirects=False)
        print(f"Login response status: {login_response.status_code}")
        
        if login_response.status_code == 302:  # Redirect means success
            print("✅ Login successful! (Redirect detected)")
            redirect_location = login_response.headers.get('Location', 'Unknown')
            print(f"Redirect to: {redirect_location}")
        else:
            print(f"❌ Login failed. Status: {login_response.status_code}")
            print(f"Response text: {login_response.text[:500]}...")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to http://127.0.0.1:5000")
        print("Make sure the Flask app is running!")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_web_login()