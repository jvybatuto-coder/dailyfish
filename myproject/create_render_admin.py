#!/usr/bin/env python
import os
import django
import sys

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User

def create_render_admin():
    username = 'render_admin'
    email = 'admin@dailyfish.com'
    password = 'RenderAdmin2024!'
    
    if User.objects.filter(username=username).exists():
        print(f"Admin user '{username}' already exists!")
        return
    
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Render admin user created successfully!")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"Email: {email}")

if __name__ == '__main__':
    create_render_admin()
