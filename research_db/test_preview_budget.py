import pandas as pd
from app import app, detect_currency_from_budget, clean_budget_amount

# Test the functions directly without database context
print("Direct function tests:")
print(f"detect_currency_from_budget('USD 50000', ''): {detect_currency_from_budget('USD 50000', '')}")
print(f"clean_budget_amount('USD 50000'): {clean_budget_amount('USD 50000')}")

# Test with different budget formats
test_budgets = ['USD 50000', '5000 US Dollars', 'Rs 25000', '€ 30000', '50000']
for budget in test_budgets:
    currency = detect_currency_from_budget(budget, '')
    amount = clean_budget_amount(budget)
    print(f"Budget: '{budget}' -> Currency: '{currency}', Amount: {amount}")

# Test what happens when budget is None or empty
print(f"\nEmpty budget: clean_budget_amount(''): {clean_budget_amount('')}")
print(f"None budget: clean_budget_amount(None): {clean_budget_amount(None)}")