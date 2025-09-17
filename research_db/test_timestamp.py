#!/usr/bin/env python3
"""
Test script to create a project and check timestamp
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Project

def test_project_creation():
    """Test creating a project and check timestamp"""
    with app.app_context():
        print("=== Testing Project Creation Timestamp ===")
        
        # Get current time
        now_before = datetime.utcnow()
        print(f"Current time before creation: {now_before}")
        
        # Create a test project
        test_project = Project(
            project_id="TEST-2025-999",
            title="Timestamp Test Project",
            description="Testing timestamp behavior",
            principal_investigator="Test Investigator",
            status="Draft"
        )
        
        print(f"Project created_at after instantiation: {test_project.created_at}")
        
        # Add to database
        db.session.add(test_project)
        db.session.commit()
        
        # Get current time after
        now_after = datetime.utcnow()
        print(f"Current time after creation: {now_after}")
        
        # Retrieve from database to see stored value
        retrieved_project = Project.query.filter_by(project_id="TEST-2025-999").first()
        if retrieved_project:
            print(f"Retrieved project created_at: {retrieved_project.created_at}")
            print(f"Retrieved project updated_at: {retrieved_project.updated_at}")
            
            # Clean up
            db.session.delete(retrieved_project)
            db.session.commit()
            print("Test project cleaned up")
        else:
            print("ERROR: Could not retrieve test project")
        
        print("\n=== Recent Projects from Database ===")
        recent_projects = Project.query.order_by(Project.created_at.desc()).limit(3).all()
        for i, project in enumerate(recent_projects, 1):
            print(f"{i}. {project.project_id} | {project.title[:30]:30s} | {project.created_at}")

if __name__ == '__main__':
    test_project_creation()