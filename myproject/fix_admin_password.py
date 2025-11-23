#!/usr/bin/env python
"""
Fix admin password script for Render
"""
import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_admin_password():
    """Fix admin user password"""
    try:
        # Set up Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
        
        import django
        django.setup()
        
        from django.contrib.auth.models import User
        from django.contrib.auth import authenticate
        
        username = 'admin'
        password = 'admin'
        
        # Get admin user
        user = User.objects.get(username=username)
        
        # Set password
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        
        # Test authentication
        auth_user = authenticate(username=username, password=password)
        if auth_user:
            print(f"SUCCESS: Admin password fixed!")
            print(f"Username: {username}")
            print(f"Password: {password}")
            return True
        else:
            print("FAILED: Authentication test failed")
            return False
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = fix_admin_password()
    sys.exit(0 if success else 1)
