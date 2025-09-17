#!/usr/bin/env python3
"""
Initialize the database with default users
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, db
from app import app
from werkzeug.security import generate_password_hash

def init_users():
    """Initialize database with default users"""
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            
            # Check if users already exist
            existing_users = User.query.count()
            if existing_users > 0:
                print(f"✅ Database already has {existing_users} users")
                return
            
            # Create default users
            default_users = [
                {
                    'username': 'manager',
                    'password': 'manager123',
                    'role': 'full_access',
                    'full_name': 'Research Manager'
                },
                {
                    'username': 'researcher',
                    'password': 'researcher123',
                    'role': 'view_all',
                    'full_name': 'Senior Researcher'
                },
                {
                    'username': 'assistant',
                    'password': 'assistant123',
                    'role': 'view_limited',
                    'full_name': 'Research Assistant'
                }
            ]
            
            print("🚀 Creating default users...")
            
            for user_data in default_users:
                # Hash the password
                hashed_password = generate_password_hash(user_data['password'])
                
                # Create user
                new_user = User(
                    username=user_data['username'],
                    password_hash=hashed_password,
                    role=user_data['role'],
                    full_name=user_data['full_name']
                )
                
                db.session.add(new_user)
                print(f"✅ Created user: {user_data['username']} (Access: {user_data['role']})")
            
            # Commit all users
            db.session.commit()
            
            print("\n🎉 Database initialization completed!")
            print("\n📝 Login Credentials:")
            print("-" * 40)
            print("Manager Account:")
            print("  Username: manager")
            print("  Password: manager123")
            print("  Access: Full access to all features")
            print()
            print("Researcher Account:")
            print("  Username: researcher")
            print("  Password: researcher123")
            print("  Access: View all projects")
            print()
            print("Assistant Account:")
            print("  Username: assistant")
            print("  Password: assistant123")
            print("  Access: View limited projects")
            
        except Exception as e:
            print(f"❌ Error initializing users: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    init_users()