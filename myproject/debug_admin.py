#!/usr/bin/env python
"""
Debug script to check admin access issues
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
from django.conf import settings

def debug_admin_access():
    """Debug admin access issues"""
    print("=== ADMIN ACCESS DEBUG ===")
    print(f"Django Settings: {settings.SETTINGS_MODULE}")
    print(f"Debug Mode: {settings.DEBUG}")
    print(f"Allowed Hosts: {settings.ALLOWED_HOSTS}")
    print(f"Database: {settings.DATABASES}")
    
    print("\n=== CHECKING ADMIN USER ===")
    try:
        admin_user = User.objects.get(username='admin')
        print(f"Admin user found: {admin_user.username}")
        print(f"Email: {admin_user.email}")
        print(f"Superuser: {admin_user.is_superuser}")
        print(f"Staff: {admin_user.is_staff}")
        print(f"Active: {admin_user.is_active}")
        print(f"Last login: {admin_user.last_login}")
    except User.DoesNotExist:
        print("Admin user NOT found!")
        return False
    
    print("\n=== TESTING AUTHENTICATION ===")
    # Test authentication
    auth_user = authenticate(username='admin', password='admin')
    if auth_user:
        print("Authentication successful!")
        print(f"Authenticated user: {auth_user.username}")
    else:
        print("Authentication failed!")
        print("Password might be incorrect")
        
        # Reset password
        print("\n=== RESETTING PASSWORD ===")
        admin_user.set_password('admin')
        admin_user.save()
        print("Password reset to 'admin'")
        
        # Test again
        auth_user = authenticate(username='admin', password='admin')
        if auth_user:
            print("Authentication successful after password reset!")
        else:
            print("Still failing - check for other issues")
    
    print("\n=== URL CONFIGURATION ===")
    try:
        from django.urls import reverse
        admin_url = reverse('admin:index')
        print(f"Admin URL: {admin_url}")
    except Exception as e:
        print(f"Admin URL error: {e}")
    
    print("\n=== RECOMMENDATIONS ===")
    print("1. Check if your Render ALLOWED_HOSTS includes your domain")
    print("2. Verify the build process ran ensure_admin command")
    print("3. Check Render logs for admin creation messages")
    print("4. Try accessing: https://your-app-name.onrender.com/admin/")
    print("5. Use credentials: admin / admin")
    
    return True

if __name__ == '__main__':
    debug_admin_access()
