import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User

username = input("Enter username: ")
email = input("Enter email: ")
password = input("Enter password: ")

try:
    user = User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully!")
except Exception as e:
    print(f"Error: {e}")