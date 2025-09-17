#!/usr/bin/env python3
"""
Fix timestamp inconsistencies in existing projects
"""

import os
import sys
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Project

def fix_project_timestamps():
    """Fix existing project timestamps to ensure consistency"""
    with app.app_context():
        print("=== Fixing Project Timestamps ===")
        
        # Get all projects
        all_projects = Project.query.all()
        print(f"Found {len(all_projects)} projects to process")
        
        # Define your timezone offset (UTC+5:30 for South Asia)
        timezone_offset = timedelta(hours=5, minutes=30)
        
        fixed_count = 0
        
        for project in all_projects:
            # Check if this looks like a local timestamp (after UTC conversion would be reasonable)
            if project.created_at:
                # If the timestamp is around 14:08:15 (2 PM), it's likely local time and needs converting to UTC
                hour = project.created_at.hour
                
                # Bulk imported projects seem to have times around 14:xx (2 PM local)
                # Manual projects have times around 08:xx (8 AM UTC = 1:30 PM local)
                if hour >= 12:  # Likely local time
                    # Convert to UTC by subtracting timezone offset
                    new_timestamp = project.created_at - timezone_offset
                    
                    print(f"Converting {project.project_id}: {project.created_at} -> {new_timestamp}")
                    project.created_at = new_timestamp
                    
                    if project.updated_at and project.updated_at.hour >= 12:
                        project.updated_at = project.updated_at - timezone_offset
                    
                    fixed_count += 1
        
        print(f"\nFixed {fixed_count} projects")
        
        if fixed_count > 0:
            print("Committing changes...")
            db.session.commit()
            print("Done!")
        else:
            print("No changes needed")
        
        print("\n=== Updated Project Order (Top 10) ===")
        recent_projects = Project.query.order_by(Project.created_at.desc()).limit(10).all()
        for i, project in enumerate(recent_projects, 1):
            created_str = project.created_at.strftime('%Y-%m-%d %H:%M:%S') if project.created_at else 'No timestamp'
            print(f"{i:2d}. {project.project_id} | {project.title[:50]:50s} | {created_str}")

if __name__ == '__main__':
    fix_project_timestamps()