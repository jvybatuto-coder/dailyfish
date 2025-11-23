import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth.models import User

try:
    admin_user = User.objects.get(username='admin')
    print(f"Admin user exists:")
    print(f"Username: {admin_user.username}")
    print(f"Email: {admin_user.email}")
    print(f"Is staff: {admin_user.is_staff}")
    print(f"Is superuser: {admin_user.is_superuser}")
    print(f"Is active: {admin_user.is_active}")
    print(f"Password hash: {admin_user.password[:50]}...")
    
    # Test password
    from django.contrib.auth import authenticate
    user = authenticate(username='admin', password='admin123')
    if user:
        print("Password authentication: SUCCESS")
    else:
        print("Password authentication: FAILED")
        
except User.DoesNotExist:
    print("Admin user does not exist!")
    
print(f"\nTotal users: {User.objects.count()}")
for user in User.objects.all():
    print(f"- {user.username} (staff: {user.is_staff}, superuser: {user.is_superuser})")