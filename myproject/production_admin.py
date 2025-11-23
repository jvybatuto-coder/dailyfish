#!/usr/bin/env python
"""
Production admin creation - more robust version
"""
import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_admin_production():
    """Create admin user in production"""
    print("=== PRODUCTION ADMIN CREATION ===")
    
    try:
        # Set up Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
        
        import django
        django.setup()
        
        from django.contrib.auth.models import User
        from django.contrib.auth import authenticate
        
        username = 'admin'
        password = 'admin'
        email = 'admin@dailyfish.com'
        
        print(f"Creating admin user: {username}")
        
        # Check if user exists
        if User.objects.filter(username=username).exists():
            print("Admin user already exists, updating password...")
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.save()
        else:
            print("Creating new admin user...")
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
        
        # Test authentication
        auth_user = authenticate(username=username, password=password)
        if auth_user:
            print("SUCCESS: Admin authentication working!")
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
    success = create_admin_production()
    print(f"Admin creation: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
