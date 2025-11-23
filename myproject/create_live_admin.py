#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command

def create_admin_user():
    """Create admin user for production deployment"""
    try:
        # Check if admin user already exists
        if User.objects.filter(username='admin').exists():
            print("Admin user already exists")
            return
        
        # Create admin user
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@dailyfish.com',
            password='admin123456',
            is_staff=True,
            is_superuser=True
        )
        print("Admin user created successfully")
        
        # Create default categories
        try:
            call_command('create_categories')
            print("Default categories created")
        except Exception as e:
            print(f"Categories creation failed: {e}")
            
    except Exception as e:
        print(f"Admin creation failed: {e}")

if __name__ == '__main__':
    create_admin_user()
