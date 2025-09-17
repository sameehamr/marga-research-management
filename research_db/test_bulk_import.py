#!/usr/bin/env python3
"""
Test bulk import functionality
"""
import sys
import os
import pandas as pd

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, Project, db
from app import app, process_import_data

def test_bulk_import():
    """Test the bulk import functionality"""
    with app.app_context():
        try:
            # Create test data
            test_data = {
                'Title': ['Test Project 1', 'Test Project 2'],
                'Principal Investigator': ['Dr. Test Smith', 'Dr. Test Jones'],
                'Description': ['Test description 1', 'Test description 2'],
                'Status': ['Active', 'Completed'],
                'Start Date': ['2024-01-01', '2023-06-15'],
                'End Date': ['2024-12-31', '2024-06-14'],
                'Budget': [10000, 20000],
                'Currency': ['USD', 'USD']
            }
            
            # Create DataFrame
            df = pd.DataFrame(test_data)
            print("✅ Test DataFrame created:")
            print(df)
            print()
            
            # Test processing
            print("🔄 Testing process_import_data...")
            processed_projects = process_import_data(df, skip_duplicates=False)
            
            print(f"✅ Processed {len(processed_projects)} projects:")
            for i, project in enumerate(processed_projects):
                print(f"  {i+1}. {project.title} - {project.principal_investigator}")
            
            print("\n🎉 Bulk import test completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during bulk import test: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_bulk_import()