#!/usr/bin/env python3
"""
Create a test Excel file for bulk import
"""
import sys
import os
import pandas as pd

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_excel():
    """Create a test Excel file with sample data"""
    try:
        # Create test data
        test_data = {
            'Title': ['Excel Test Project 1', 'Excel Test Project 2', 'Excel Test Project 3'],
            'Principal Investigator': ['Dr. Excel Smith', 'Dr. Excel Jones', 'Dr. Excel Brown'],
            'Description': ['Excel test description 1', 'Excel test description 2', 'Excel test description 3'],
            'Status': ['Active', 'Completed', 'On Hold'],
            'Start Date': ['2024-01-01', '2023-06-15', '2024-03-01'],
            'End Date': ['2024-12-31', '2024-06-14', '2025-02-28'],
            'Team Members': ['Alice, Bob', 'Carol, Dave', 'Eve, Frank'],
            'Funding Source': ['NSF Grant', 'University Fund', 'Private Donor'],
            'Budget': [75000, 45000, 60000],
            'Currency': ['USD', 'USD', 'USD'],
            'Category': ['Medical Research', 'Environmental', 'Technology'],
            'Theme': ['Cancer Research', 'Climate Change', 'AI Development']
        }
        
        # Create DataFrame
        df = pd.DataFrame(test_data)
        
        # Save as Excel file
        excel_filename = 'test_import.xlsx'
        df.to_excel(excel_filename, index=False, engine='openpyxl')
        
        print(f"✅ Created test Excel file: {excel_filename}")
        print(f"📊 Contains {len(df)} rows of sample data")
        print("\nColumns:")
        for col in df.columns:
            print(f"  - {col}")
        
        print(f"\nFirst few rows:")
        print(df.head())
        
        # Test reading the file back
        print(f"\n🔄 Testing reading the Excel file...")
        df_read = pd.read_excel(excel_filename, engine='openpyxl')
        print(f"✅ Successfully read {len(df_read)} rows from Excel file")
        
        return excel_filename
        
    except Exception as e:
        print(f"❌ Error creating test Excel file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    create_test_excel()