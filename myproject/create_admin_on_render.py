#!/usr/bin/env python
"""
Create admin user on Render deployment
This script can be run manually on Render or called from build process
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

def create_admin_on_render():
    """Create admin user on Render deployment"""
    username = 'admin'
    password = 'admin123'
    email = 'admin@dailyfish.com'
    
    try:
        # Check if user exists
        if User.objects.filter(username=username).exists():
            print(f"✅ Admin user '{username}' already exists")
            user = User.objects.get(username=username)
            # Reset password to ensure it works
            user.set_password(password)
            user.save()
            print(f"🔒 Password reset to '{password}' for safety")
        else:
            # Create new admin user
            user = User.objects.create_superuser(username=username, email=email, password=password)
            print(f"✅ Admin user '{username}' created successfully!")
        
        print(f"📋 Login details:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Email: {email}")
        print(f"🌐 Admin URL: https://your-app-name.onrender.com/admin/")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin: {str(e)}")
        return False

if __name__ == '__main__':
    success = create_admin_on_render()
    sys.exit(0 if success else 1)
