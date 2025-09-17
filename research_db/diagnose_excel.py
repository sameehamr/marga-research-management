#!/usr/bin/env python3
"""
Diagnose Excel file import issues
"""
import sys
import os
import pandas as pd

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, process_import_data

def diagnose_excel_file(filename):
    """Diagnose issues with an Excel file for import"""
    print(f"🔍 Diagnosing Excel file: {filename}")
    print("=" * 50)
    
    # Check if file exists
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return False
    
    try:
        # Try to read the Excel file
        print("📖 Attempting to read Excel file...")
        df = pd.read_excel(filename, engine='openpyxl')
        print(f"✅ Successfully read Excel file")
        print(f"📊 Shape: {df.shape[0]} rows, {df.shape[1]} columns")
        
        # Show column names
        print(f"\n📋 Column names found:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i}. '{col}'")
        
        # Show first few rows
        print(f"\n👀 First 3 rows of data:")
        print(df.head(3))
        
        # Check for required columns
        print(f"\n🔍 Checking for required columns...")
        required_columns = ['title', 'principal investigator']
        
        # Column mapping (flexible column names)
        column_mapping = {
            'title': ['title', 'project title', 'name', 'project name'],
            'principal_investigator': ['principal investigator', 'pi', 'lead', 'principal_investigator'],
        }
        
        df_columns = {col.lower().strip(): col for col in df.columns}
        missing_requirements = []
        
        for field, possible_names in column_mapping.items():
            found = False
            for name in possible_names:
                if name.lower() in df_columns:
                    print(f"  ✅ Found {field}: '{df_columns[name.lower()]}'")
                    found = True
                    break
            if not found:
                missing_requirements.append(field)
                print(f"  ❌ Missing {field} (looking for: {', '.join(possible_names)})")
        
        if missing_requirements:
            print(f"\n❌ Cannot import: Missing required columns: {', '.join(missing_requirements)}")
            print(f"\n💡 Suggestions:")
            print(f"  - Make sure your Excel file has columns named 'Title' and 'Principal Investigator'")
            print(f"  - Check for extra spaces or special characters in column names")
            print(f"  - Ensure the first row contains column headers")
            return False
        
        # Test processing
        print(f"\n🔄 Testing data processing...")
        with app.app_context():
            processed_projects = process_import_data(df, skip_duplicates=False)
            print(f"✅ Successfully processed {len(processed_projects)} projects")
            
            if processed_projects:
                print(f"\n📝 Sample processed projects:")
                for i, project in enumerate(processed_projects[:3], 1):
                    print(f"  {i}. {project.title} - {project.principal_investigator} (ID: {project.project_id})")
            else:
                print(f"⚠️ No projects were processed - check your data")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading/processing Excel file: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main diagnostic function"""
    # Test with our known good file first
    print("🧪 Testing with known good Excel file...")
    if diagnose_excel_file('test_import.xlsx'):
        print("\n✅ Known good file works correctly")
    else:
        print("\n❌ Issue with test file - Excel functionality may be broken")
        return
    
    # Look for user Excel files
    print(f"\n" + "="*70)
    print("🔍 Looking for Excel files in current directory...")
    excel_files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls')) and f != 'test_import.xlsx']
    
    if excel_files:
        print(f"Found {len(excel_files)} Excel file(s):")
        for i, file in enumerate(excel_files, 1):
            print(f"  {i}. {file}")
        
        print(f"\n🔍 Diagnosing each file...")
        for file in excel_files:
            print(f"\n" + "-"*50)
            diagnose_excel_file(file)
    else:
        print("No additional Excel files found in current directory")
        print("\n💡 To diagnose your Excel file:")
        print("  1. Copy your Excel file to this directory")
        print("  2. Run: python diagnose_excel.py")

if __name__ == "__main__":
    main()