import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User

# Create admin user for live server
try:
    if not User.objects.filter(username='liveadmin').exists():
        User.objects.create_superuser(
            username='liveadmin',
            email='admin@dailyfish.com',
            password='dailyfish2024'
        )
        print("Live admin user created successfully!")
    else:
        print("Live admin user already exists")
except Exception as e:
    print(f"Error creating admin user: {e}")