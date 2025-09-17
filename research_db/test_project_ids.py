#!/usr/bin/env python3
"""
Test project ID generation for bulk imports
"""
import sys
import os
import pandas as pd

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, Project, db
from app import app, process_import_data

def test_unique_project_ids():
    """Test that project IDs are unique during bulk import"""
    with app.app_context():
        try:
            # Create test data with multiple projects for the same year
            test_data = {
                'Title': [
                    'Test Project A', 'Test Project B', 'Test Project C', 
                    'Test Project D', 'Test Project E'
                ],
                'Principal Investigator': [
                    'Dr. Smith A', 'Dr. Smith B', 'Dr. Smith C',
                    'Dr. Smith D', 'Dr. Smith E'
                ],
                'Description': [
                    'Description A', 'Description B', 'Description C',
                    'Description D', 'Description E'
                ],
                'Status': ['Active'] * 5,
                'Start Date': ['2024-01-01'] * 5,
                'End Date': ['2024-12-31'] * 5,  # Same year for all
                'Budget': [10000, 20000, 30000, 40000, 50000],
                'Currency': ['USD'] * 5
            }
            
            # Create DataFrame
            df = pd.DataFrame(test_data)
            print("✅ Test DataFrame created:")
            print(df[['Title', 'Principal Investigator', 'End Date']])
            print()
            
            # Test processing
            print("🔄 Testing process_import_data with unique ID generation...")
            processed_projects = process_import_data(df, skip_duplicates=False)
            
            print(f"✅ Processed {len(processed_projects)} projects:")
            project_ids = []
            for i, project in enumerate(processed_projects):
                print(f"  {i+1}. {project.title} - ID: {project.project_id}")
                project_ids.append(project.project_id)
            
            # Check for duplicates
            unique_ids = set(project_ids)
            if len(unique_ids) == len(project_ids):
                print(f"\n✅ All {len(project_ids)} project IDs are unique!")
                print(f"Generated IDs: {', '.join(sorted(project_ids))}")
            else:
                print(f"\n❌ Found duplicate project IDs!")
                print(f"Total IDs: {len(project_ids)}, Unique IDs: {len(unique_ids)}")
                duplicates = [id for id in project_ids if project_ids.count(id) > 1]
                print(f"Duplicates: {set(duplicates)}")
            
            print("\n🎉 Project ID generation test completed!")
            
        except Exception as e:
            print(f"❌ Error during project ID test: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_unique_project_ids()