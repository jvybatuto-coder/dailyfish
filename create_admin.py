import os
import sys
import django

# Add the project directory to Python path
sys.path.append(r'C:\Users\harold japay\Desktop\dailyfish\myproject')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# Setup Django
django.setup()

from django.contrib.auth.models import User

# Create or update the user
username = "pelaez"
password = "pelaez123"

try:
    # Check if user already exists
    user = User.objects.get(username=username)
    print(f"User '{username}' already exists. Updating permissions...")
except User.DoesNotExist:
    # Create new user
    user = User.objects.create_user(username=username, password=password)
    print(f"Created new user '{username}'")

# Set staff and superuser permissions
user.is_staff = True
user.is_superuser = True
user.is_active = True
user.save()

print(f"✅ User '{username}' now has admin access!")
print(f"🔐 Username: {username}")
print(f"🔐 Password: {password}")
print("🌐 You can now login at: https://your-domain.com/admin/")
