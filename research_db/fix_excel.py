#!/usr/bin/env python3
"""
Fix the existing Excel file by adding the missing Principal Investigator column
"""
import pandas as pd
import os

def fix_excel_file():
    """Fix the Research Grants - Marga.xlsx file by adding missing column"""
    filename = 'Research Grants - Marga.xlsx'
    
    try:
        print(f"🔧 Fixing Excel file: {filename}")
        
        # Read the existing file
        df = pd.read_excel(filename, engine='openpyxl')
        print(f"📖 Read {len(df)} rows from original file")
        print(f"Original columns: {list(df.columns)}")
        
        # Add the missing Principal Investigator column
        # Set a default value - you can change this to actual PIs later
        df['Principal Investigator'] = 'Dr. TBD'  # TBD = To Be Determined
        
        # Reorder columns to put required ones first
        desired_order = [
            'title', 'Principal Investigator', 'funding_source', 
            'start_date', 'end_date', 'budget', 'Status'
        ]
        
        # Only include columns that exist
        available_columns = [col for col in desired_order if col in df.columns]
        df_reordered = df[available_columns]
        
        # Rename columns to match expected format (capitalize first letters)
        column_mapping = {
            'title': 'Title',
            'Principal Investigator': 'Principal Investigator',
            'funding_source': 'Funding Source',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'budget': 'Budget',
            'Status': 'Status'
        }
        
        df_final = df_reordered.rename(columns=column_mapping)
        
        # Save the fixed file
        fixed_filename = 'Research Grants - Marga - Fixed.xlsx'
        df_final.to_excel(fixed_filename, index=False, engine='openpyxl')
        
        print(f"✅ Created fixed file: {fixed_filename}")
        print(f"📊 Final columns: {list(df_final.columns)}")
        print(f"📝 Sample data:")
        print(df_final.head(3))
        
        print(f"\n💡 Next steps:")
        print(f"1. Open '{fixed_filename}' in Excel")
        print(f"2. Replace 'Dr. TBD' values with actual Principal Investigator names")
        print(f"3. Save the file")
        print(f"4. Use the bulk import feature in the web application")
        
        return fixed_filename
        
    except Exception as e:
        print(f"❌ Error fixing Excel file: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    fix_excel_file()