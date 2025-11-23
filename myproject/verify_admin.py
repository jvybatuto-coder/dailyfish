#!/usr/bin/env python
"""
Check if admin user exists and can login
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def check_admin():
    """Check if admin user exists and can authenticate"""
    username = 'admin'
    password = 'admin123'
    
    print(f"Checking admin user '{username}'...")
    
    # Check if user exists
    try:
        user = User.objects.get(username=username)
        print(f"✓ User exists: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Superuser: {user.is_superuser}")
        print(f"  Staff: {user.is_staff}")
        print(f"  Active: {user.is_active}")
    except User.DoesNotExist:
        print(f"✗ User '{username}' does not exist!")
        return False
    
    # Test authentication
    auth_user = authenticate(username=username, password=password)
    if auth_user:
        print(f"✓ Authentication successful!")
        print(f"✓ Admin login should work at: /admin/")
    else:
        print(f"✗ Authentication failed!")
        print(f"✗ Check password or user permissions")
        return False
    
    return True

if __name__ == '__main__':
    success = check_admin()
    sys.exit(0 if success else 1)
