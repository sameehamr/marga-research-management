#!/usr/bin/env python3
"""
Simple test to reproduce the Flask database error
"""

import os
import sys

# Add the research_db directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Project

def test_database():
    """Test database operations that were failing"""
    
    with app.app_context():
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Check if we can connect
        try:
            db.engine.connect()
            print("✅ Database connection successful")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return
        
        # Test the specific query that was failing
        try:
            print("Testing project count...")
            total_projects = Project.query.count()
            print(f"✅ Total projects: {total_projects}")
            
            print("Testing projects with budget...")
            projects_with_budget = Project.query.filter(Project.budget.isnot(None)).all()
            print(f"✅ Projects with budget: {len(projects_with_budget)}")
            
            print("Testing currency access...")
            for project in projects_with_budget[:3]:
                print(f"  {project.project_id}: {project.currency}")
            
        except Exception as e:
            print(f"❌ Query failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_database()