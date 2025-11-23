import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User

User.objects.create_superuser(
    username='newadmin',
    email='newadmin@dailyfish.com',
    password='newadmin123'
)
print("Superuser 'newadmin' created with password 'newadmin123'")