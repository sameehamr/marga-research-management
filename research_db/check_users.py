#!/usr/bin/env python3
"""
Quick script to check user accounts in the database
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, db
from app import app

def check_users():
    """Check and display all user accounts"""
    with app.app_context():
        try:
            users = User.query.all()
            if users:
                print("\n🔐 Available User Accounts:")
                print("-" * 50)
                for user in users:
                    print(f"Username: {user.username}")
                    print(f"Full Name: {user.full_name}")
                    print(f"Role: {user.role}")
                    print(f"ID: {user.id}")
                    print("-" * 30)
                    
                print("\n📝 Standard Login Credentials:")
                print("Username: manager   | Password: manager123")
                print("Username: researcher| Password: researcher123")
                print("Username: assistant | Password: assistant123")
                
            else:
                print("❌ No users found in the database")
                print("The database might need to be initialized with default users")
                
        except Exception as e:
            print(f"❌ Error checking users: {str(e)}")

if __name__ == "__main__":
    check_users()