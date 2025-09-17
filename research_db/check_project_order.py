#!/usr/bin/env python3
"""
Quick script to check project ordering in the database
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Project

def check_project_order():
    """Check the current project order in database"""
    with app.app_context():
        print("=== Checking Project Order ===")
        print(f"Current time: {datetime.now()}")
        print(f"Current UTC time: {datetime.utcnow()}")
        print()
        print("All projects ordered by created_at DESC (newest first):")
        print()
        
        projects = Project.query.order_by(Project.created_at.desc()).all()
        
        if not projects:
            print("No projects found in database.")
            return
        
        for i, project in enumerate(projects, 1):
            created_str = project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else 'No timestamp'
            print(f"{i:2d}. {project.project_id} | {project.title[:50]:50s} | {created_str}")
        
        print()
        print("=== Specifically checking the 'testtest' project ===")
        testtest_project = Project.query.filter(Project.title.ilike('%testtest%')).first()
        if testtest_project:
            print(f"Project ID: {testtest_project.project_id}")
            print(f"Title: {testtest_project.title}")
            print(f"Created at: {testtest_project.created_at}")
            print(f"Updated at: {testtest_project.updated_at}")
            print(f"Status: {testtest_project.status}")
        else:
            print("No 'testtest' project found")
            
        print()
        print("=== Most recent 5 projects by ID ===")
        recent_by_id = Project.query.order_by(Project.id.desc()).limit(5).all()
        for i, project in enumerate(recent_by_id, 1):
            created_str = project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else 'No timestamp'
            print(f"{i}. ID:{project.id} | {project.project_id} | {project.title[:30]:30s} | {created_str}")

if __name__ == '__main__':
    check_project_order()