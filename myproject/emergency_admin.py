#!/usr/bin/env python
"""
Emergency admin creation script for Render deployment
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

def emergency_admin():
    """Emergency admin creation"""
    username = 'admin'
    password = 'admin'
    email = 'admin@dailyfish.com'
    
    print("=== EMERGENCY ADMIN CREATION ===")
    
    try:
        # Delete existing admin user if found
        existing_users = User.objects.filter(username=username)
        if existing_users.exists():
            print(f"Deleting existing admin user(s): {existing_users.count()} found")
            existing_users.delete()
        
        # Create new admin user
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        
        print(f"Admin user '{username}' created successfully!")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Email: {email}")
        
        # Verify authentication
        from django.contrib.auth import authenticate
        auth_user = authenticate(username=username, password=password)
        if auth_user:
            print("Authentication test: PASSED")
        else:
            print("Authentication test: FAILED")
            
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == '__main__':
    success = emergency_admin()
    sys.exit(0 if success else 1)
