import pandas as pd
from app import app, detect_currency_from_budget, clean_budget_amount

# Test different scenarios that might occur in Excel files
test_scenarios = [
    # Scenario 1: USD with amount
    {'Title': 'Project 1', 'Principal Investigator': 'John Doe', 'Budget': 'USD 50000'},
    
    # Scenario 2: US Dollars with amount  
    {'Title': 'Project 2', 'Principal Investigator': 'Jane Smith', 'Budget': '5000 US Dollars'},
    
    # Scenario 3: Rupees with amount
    {'Title': 'Project 3', 'Principal Investigator': 'Bob Wilson', 'Budget': 'Rs 25000'},
    
    # Scenario 4: Empty budget
    {'Title': 'Project 4', 'Principal Investigator': 'Alice Brown', 'Budget': ''},
    
    # Scenario 5: Only number
    {'Title': 'Project 5', 'Principal Investigator': 'Charlie Davis', 'Budget': '75000'},
    
    # Scenario 6: Currency in separate column
    {'Title': 'Project 6', 'Principal Investigator': 'David Miller', 'Budget': '30000', 'Currency': 'EUR'},
]

print("Testing budget and currency detection:")
print("=" * 60)

for i, scenario in enumerate(test_scenarios, 1):
    budget_text = scenario.get('Budget', '')
    currency_text = scenario.get('Currency', '')
    
    detected_currency = detect_currency_from_budget(budget_text, currency_text)
    cleaned_amount = clean_budget_amount(budget_text)
    
    print(f"Scenario {i}: {scenario['Title']}")
    print(f"  Budget text: '{budget_text}'")
    print(f"  Currency text: '{currency_text}'")
    print(f"  Detected currency: '{detected_currency}'")
    print(f"  Cleaned amount: {cleaned_amount}")
    
    # Show what would appear in preview
    if cleaned_amount:
        preview_text = f"{detected_currency} {cleaned_amount}"
    elif detected_currency:
        preview_text = f"{detected_currency} (Amount not specified)"
    else:
        preview_text = "Not specified"
    
    print(f"  Preview display: '{preview_text}'")
    print()