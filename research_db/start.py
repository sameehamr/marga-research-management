#!/usr/bin/env python3
"""
Marga Research Institute Management System
Simple startup script for production use
"""
import os
import sys

def start_application():
    """Start the Flask application"""
    try:
        # Change to the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Check if required files exist
        required_files = ['app.py', 'models.py', 'research_projects.db']
        missing_files = [f for f in required_files if not os.path.exists(f)]
        
        if missing_files:
            print("❌ Missing required files:")
            for file in missing_files:
                print(f"   - {file}")
            return False
        
        # Check if templates directory exists
        if not os.path.exists('templates'):
            print("❌ Missing templates directory")
            return False
        
        print("✅ All required files found")
        print("🚀 Starting Marga Institute Database Management System...")
        
        # Import and run the app
        from app import app
        app.run(debug=False, host='127.0.0.1', port=5000)
        
    except Exception as e:
        print(f"❌ Error starting application: {str(e)}")
        return False

if __name__ == "__main__":
    start_application()
