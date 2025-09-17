#!/usr/bin/env python3
"""
Test user authentication
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, db
from app import app
from werkzeug.security import check_password_hash

def test_login(username, password):
    """Test login credentials"""
    with app.app_context():
        try:
            # Find user
            user = User.query.filter_by(username=username).first()
            
            if not user:
                print(f"❌ User '{username}' not found in database")
                return False
            
            # Check password
            if check_password_hash(user.password_hash, password):
                print(f"✅ Login successful for '{username}'")
                print(f"   Full Name: {user.full_name}")
                print(f"   Role: {user.role}")
                return True
            else:
                print(f"❌ Wrong password for '{username}'")
                print(f"   Stored password hash: {user.password_hash[:50]}...")
                return False
                
        except Exception as e:
            print(f"❌ Error testing login: {str(e)}")
            return False

def test_all_users():
    """Test all default users"""
    print("🔍 Testing all default user credentials...")
    print("-" * 50)
    
    test_cases = [
        ('manager', 'manager123'),
        ('researcher', 'researcher123'),
        ('assistant', 'assistant123')
    ]
    
    for username, password in test_cases:
        print(f"\nTesting {username}:")
        test_login(username, password)

if __name__ == "__main__":
    test_all_users()