import os
import sys
import django

# Add the project directory to Python path
sys.path.append(r'C:\Users\harold japay\Desktop\dailyfish\myproject')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# Setup Django
django.setup()

from django.contrib.auth.models import User

# Get the user and update password
username = "pelaez"
password = "pelaez123"

try:
    user = User.objects.get(username=username)
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.save()
    
    print(f"✅ Updated password for user '{username}'")
    print(f"🔐 Username: {username}")
    print(f"🔐 Password: {password}")
    print("🌐 Try logging in again at: https://your-domain.com/admin/")
    print("📱 Make sure you're using your correct Render domain!")
    
except User.DoesNotExist:
    print(f"❌ User '{username}' not found")
