#!/usr/bin/env python3
"""
Debug login issue by checking what the login route actually returns
"""
import requests
from bs4 import BeautifulSoup
import sys
import os

def debug_login():
    """Debug login by parsing the actual HTML response"""
    base_url = "http://127.0.0.1:5000"
    
    try:
        session = requests.Session()
        
        # Get login page
        print("🔍 Getting login page...")
        login_page = session.get(f"{base_url}/login", timeout=5)
        print(f"Login page status: {login_page.status_code}")
        
        # Submit login
        print("\n🔐 Submitting login...")
        login_data = {
            'username': 'manager',
            'password': 'manager123'
        }
        
        response = session.post(f"{base_url}/login", data=login_data, timeout=5)
        print(f"Response status: {response.status_code}")
        
        # Parse HTML to find error messages
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for Flash messages
        flash_messages = soup.find_all(class_=['alert', 'flash-message'])
        if flash_messages:
            print("\n📢 Flash messages found:")
            for msg in flash_messages:
                print(f"  {msg.get_text().strip()}")
        
        # Look for error messages in forms
        error_divs = soup.find_all(class_=['error', 'text-danger', 'alert-danger'])
        if error_divs:
            print("\n❌ Error messages found:")
            for error in error_divs:
                print(f"  {error.get_text().strip()}")
        
        # Check if we're redirected to dashboard
        title = soup.find('title')
        if title:
            print(f"\n📄 Page title: {title.get_text().strip()}")
            if 'Dashboard' in title.get_text():
                print("✅ Successfully logged in! (Dashboard detected)")
            elif 'Login' in title.get_text():
                print("❌ Still on login page - login failed")
        
        # Check for any indication of successful login
        user_info = soup.find(class_=['user-info', 'username', 'welcome'])
        if user_info:
            print(f"\n👤 User info found: {user_info.get_text().strip()}")
        
        # Print a small sample of the response for debugging
        print(f"\n📋 Response preview (first 300 chars):")
        print(response.text[:300] + "..." if len(response.text) > 300 else response.text)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    debug_login()