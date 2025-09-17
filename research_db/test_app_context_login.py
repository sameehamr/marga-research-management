#!/usr/bin/env python3
"""
Test login using the same Flask app context as the running server
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, db
from app import app
from werkzeug.security import check_password_hash

def test_login_with_app_context():
    """Test login within Flask app context"""
    with app.app_context():
        try:
            print("🔍 Testing login within Flask app context...")
            
            # Test the exact same logic as the login route
            username = 'manager'
            password = 'manager123'
            
            print(f"Looking for user: {username}")
            user = User.query.filter_by(username=username).first()
            
            if not user:
                print(f"❌ User '{username}' not found!")
                return
            
            print(f"✅ User found: {user.username}")
            print(f"   Full name: {user.full_name}")
            print(f"   Role: {user.role}")
            print(f"   Active: {user.is_active}")
            print(f"   Password hash: {user.password_hash[:50]}...")
            
            # Test password check
            print(f"\nTesting password: {password}")
            password_valid = check_password_hash(user.password_hash, password)
            
            if password_valid:
                print("✅ Password is VALID!")
                print("✅ Login should work!")
            else:
                print("❌ Password is INVALID!")
                
                # Try regenerating the password hash to see if there's an issue
                from werkzeug.security import generate_password_hash
                new_hash = generate_password_hash(password)
                print(f"New hash would be: {new_hash[:50]}...")
                
                # Test if new hash works
                if check_password_hash(new_hash, password):
                    print("✅ New hash works - there might be an issue with the stored hash")
                else:
                    print("❌ Even new hash doesn't work - bigger issue")
            
            # Also test other accounts
            print("\n🔍 Testing all accounts...")
            all_users = User.query.all()
            test_passwords = {
                'manager': 'manager123',
                'researcher': 'researcher123',
                'assistant': 'assistant123'
            }
            
            for user in all_users:
                test_password = test_passwords.get(user.username)
                if test_password:
                    is_valid = check_password_hash(user.password_hash, test_password)
                    status = "✅" if is_valid else "❌"
                    print(f"{status} {user.username}: {test_password}")
                    
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_login_with_app_context()