#!/usr/bin/env python
"""
Force create admin user - delete existing if found and create fresh
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

def force_create_admin():
    """Force create admin by deleting existing and creating new"""
    username = 'admin'
    password = 'admin123'
    email = 'admin@dailyfish.com'
    
    try:
        # Delete existing admin user if found
        existing_users = User.objects.filter(username=username)
        if existing_users.exists():
            print(f"🗑️ Deleting existing admin user(s): {existing_users.count()} found")
            existing_users.delete()
        
        # Create new admin user
        user = User.objects.create_superuser(username=username, email=email, password=password)
        
        print(f"✅ Admin user '{username}' created successfully!")
        print(f"📋 Login details:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Email: {email}")
        print(f"🌐 Admin URL: https://your-app-name.onrender.com/admin/")
        
        # Verify user can authenticate
        from django.contrib.auth import authenticate
        auth_user = authenticate(username=username, password=password)
        if auth_user:
            print(f"✅ Authentication test passed!")
        else:
            print(f"❌ Authentication test failed!")
            
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin: {str(e)}")
        return False

if __name__ == '__main__':
    success = force_create_admin()
    sys.exit(0 if success else 1)
