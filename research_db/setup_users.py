#!/usr/bin/env python3
"""
Setup default users for the application
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, db
from app import app
from werkzeug.security import generate_password_hash

def setup_users():
    """Setup default users"""
    with app.app_context():
        try:
            # Create tables if they don't exist
            db.create_all()
            
            # Check existing users
            existing_users = User.query.all()
            print(f"Current users in database: {len(existing_users)}")
            
            for user in existing_users:
                print(f"- {user.username} ({user.role})")
            
            # If no users exist, create them
            if len(existing_users) == 0:
                print("\n🚀 Creating default users...")
                
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
                    print(f"✅ Created user: {user_data['username']}")
                
                # Commit all users
                db.session.commit()
                print("\n🎉 Users created successfully!")
            
            print("\n📝 Login Credentials:")
            print("-" * 40)
            print("Manager Account (Full Access):")
            print("  Username: manager")
            print("  Password: manager123")
            print()
            print("Researcher Account (View All):")
            print("  Username: researcher")
            print("  Password: researcher123")
            print()
            print("Assistant Account (View Limited):")
            print("  Username: assistant")
            print("  Password: assistant123")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    setup_users()