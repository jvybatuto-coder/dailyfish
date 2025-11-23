import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User

# Delete existing admin user if exists
try:
    User.objects.get(username='admin').delete()
    print("Deleted existing admin user")
except User.DoesNotExist:
    pass

# Create new admin user
admin_user = User.objects.create_superuser(
    username='admin',
    email='admin@dailyfish.com',
    password='admin123'
)
print("New admin user created successfully!")
print("Username: admin")
print("Password: admin123")