#!/usr/bin/env python3
"""
Test login functionality programmatically
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, db
from app import app
from werkzeug.security import check_password_hash

def test_login():
    """Test login credentials"""
    with app.app_context():
        try:
            print("🔐 Testing login credentials...")
            
            # Test all user accounts
            test_accounts = [
                ('manager', 'manager123'),
                ('researcher', 'researcher123'),
                ('assistant', 'assistant123')
            ]
            
            for username, password in test_accounts:
                user = User.query.filter_by(username=username).first()
                
                if not user:
                    print(f"❌ User '{username}' not found in database")
                    continue
                
                if check_password_hash(user.password_hash, password):
                    print(f"✅ {username}: Login credentials are VALID")
                    print(f"   Full Name: {user.full_name}")
                    print(f"   Role: {user.role}")
                    print(f"   Active: {user.is_active}")
                else:
                    print(f"❌ {username}: Login credentials are INVALID")
                    print(f"   Password hash: {user.password_hash[:50]}...")
                
                print()
                
        except Exception as e:
            print(f"❌ Error testing login: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_login()