import requests
import sys

# Test the new routes to see if they're accessible
base_url = "http://127.0.0.1:5000"

def test_route(route, description):
    try:
        response = requests.get(f"{base_url}{route}")
        status = "✅ Working" if response.status_code in [200, 302] else f"❌ Error {response.status_code}"
        print(f"{description}: {status}")
        return response.status_code in [200, 302]
    except Exception as e:
        print(f"{description}: ❌ Failed to connect - {str(e)}")
        return False

print("🔍 Testing New Features Accessibility:")
print("=" * 50)

# Test basic routes
test_route("/", "Homepage")
test_route("/login", "Login Page") 
test_route("/forgot-password", "Forgot Password Page")
test_route("/dashboard", "Dashboard (redirects to login)")
test_route("/users", "User Management (requires login)")
test_route("/admin/backup", "Backup System (requires login)")

print("\n📝 To see the changes:")
print("1. Open http://127.0.0.1:5000 in your browser")
print("2. Log in with: manager/manager123")
print("3. Look for new navigation items: Users, Backup, Change Password")
print("4. Check the enhanced dashboard with admin sections")
print("5. Try accessing User Management and Backup System")

# Check if there are any import errors in the app
try:
    import sys
    sys.path.append('.')
    from app import app
    print("\n✅ App imports successfully - no syntax errors")
except Exception as e:
    print(f"\n❌ App import error: {e}")