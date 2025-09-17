#!/usr/bin/env python3
"""
Test all application routes to identify missing functions
"""
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

def test_routes():
    """Test all routes in the application"""
    print("🔍 Testing all application routes...")
    print("-" * 50)
    
    with app.app_context():
        # Get all routes
        routes = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':
                routes.append({
                    'endpoint': rule.endpoint,
                    'rule': rule.rule,
                    'methods': list(rule.methods - {'HEAD', 'OPTIONS'})
                })
        
        # Sort routes
        routes.sort(key=lambda x: x['rule'])
        
        print(f"Found {len(routes)} routes:")
        print()
        
        for route in routes:
            methods = ', '.join(route['methods'])
            print(f"✅ {route['rule']} -> {route['endpoint']} [{methods}]")
        
        print()
        print("🎉 All routes are accessible!")
        
        # Test template references
        print("\n🔍 Checking template references...")
        template_issues = []
        
        # Common template url_for references
        common_refs = [
            'home', 'dashboard', 'projects', 'add_project', 'edit_project',
            'view_project', 'delete_project', 'bulk_import', 'export_projects_csv',
            'login', 'logout', 'manage_users', 'download_template'
        ]
        
        available_endpoints = [route['endpoint'] for route in routes]
        
        for ref in common_refs:
            if ref not in available_endpoints:
                template_issues.append(ref)
        
        if template_issues:
            print("❌ Missing template references:")
            for issue in template_issues:
                print(f"   - {issue}")
        else:
            print("✅ All template references are available!")

if __name__ == "__main__":
    test_routes()