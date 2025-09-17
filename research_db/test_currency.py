#!/usr/bin/env python3
"""
Test the improved currency handling
"""
import sys
import os
import pandas as pd

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, detect_currency_from_budget, clean_budget_amount, process_import_data

def test_currency_handling():
    """Test currency detection and budget parsing"""
    print("🧪 Testing Currency Detection & Budget Parsing")
    print("=" * 50)
    
    # Test currency detection
    test_cases = [
        ('Rs 50000', '', 'Rs'),
        ('USD 25000', '', 'USD'),
        ('€ 30000', '', 'EUR'),
        ('£ 20000', '', 'GBP'),
        ('¥ 100000', '', 'JPY'),
        ('₹ 75000', '', 'INR'),
        ('50000', 'Rs', 'Rs'),
        ('25000', 'USD', 'USD'),
        ('1000000 Sri Lankan Rupees', '', 'Rs'),
        ('5000 US Dollars', '', 'USD'),
        ('', 'THB', 'THB'),
        ('', '', 'Rs'),  # Default
    ]
    
    print("🔍 Testing Currency Detection:")
    for budget_text, currency_text, expected in test_cases:
        result = detect_currency_from_budget(budget_text, currency_text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{budget_text}' + '{currency_text}' → {result} (expected: {expected})")
    
    # Test budget amount extraction
    budget_test_cases = [
        ('Rs 50000', 50000.0),
        ('USD 25,000', 25000.0),
        ('€ 30,000.50', 30000.5),
        ('50000', 50000.0),
        ('1,250,000', 1250000.0),
        ('Rs 1,50,000', 150000.0),  # Indian numbering
        ('$25,000.75', 25000.75),
        ('', None),
        ('invalid', None),
    ]
    
    print("\n💰 Testing Budget Amount Extraction:")
    for budget_text, expected in budget_test_cases:
        result = clean_budget_amount(budget_text)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{budget_text}' → {result} (expected: {expected})")
    
    # Test with DataFrame
    print("\n📊 Testing with DataFrame (Multi-Currency):")
    test_data = {
        'Title': ['Project A', 'Project B', 'Project C', 'Project D'],
        'Principal Investigator': ['Dr. A', 'Dr. B', 'Dr. C', 'Dr. D'],
        'Budget': ['Rs 500000', 'USD 25,000', '€ 30000', '₹ 75,000'],
        'Currency': ['', '', '', 'INR'],  # Some empty, some filled
        'Status': ['Active'] * 4,
    }
    
    df = pd.DataFrame(test_data)
    
    with app.app_context():
        projects = process_import_data(df)
        
        print(f"✅ Processed {len(projects)} projects:")
        for project in projects:
            print(f"  • {project.title}: {project.currency} {project.budget}")

if __name__ == "__main__":
    test_currency_handling()