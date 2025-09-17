#!/usr/bin/env python3
"""
Reset manager password to ensure it works
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, db
from app import app
from werkzeug.security import generate_password_hash, check_password_hash

def reset_manager_password():
    """Reset manager password"""
    with app.app_context():
        try:
            # Find manager user
            manager = User.query.filter_by(username='manager').first()
            
            if not manager:
                print("❌ Manager user not found!")
                return
                
            # Set new password
            new_password = 'manager123'
            new_hash = generate_password_hash(new_password)
            
            print(f"🔄 Resetting manager password...")
            print(f"Old hash: {manager.password_hash[:50]}...")
            print(f"New hash: {new_hash[:50]}...")
            
            # Update password
            manager.password_hash = new_hash
            db.session.commit()
            
            # Test the new password
            if check_password_hash(manager.password_hash, new_password):
                print("✅ Password reset successful!")
                print("✅ Password verification successful!")
                print(f"Username: manager")
                print(f"Password: {new_password}")
            else:
                print("❌ Password verification failed!")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    reset_manager_password()