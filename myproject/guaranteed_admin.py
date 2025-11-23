#!/usr/bin/env python
"""
GUARANTEED admin creation - runs on every request if needed
"""
import os
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def ensure_admin_exists():
    """Ensure admin user exists - call this from views"""
    try:
        # Set up Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
        
        import django
        django.setup()
        
        from django.contrib.auth.models import User
        from django.contrib.auth import authenticate
        
        username = 'admin'
        password = 'admin'
        email = 'admin@dailyfish.com'
        
        # Check if admin exists and can authenticate
        auth_user = authenticate(username=username, password=password)
        if auth_user:
            return True  # Admin already exists and works
        
        # Create admin if not exists or auth fails
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.is_active = True
            user.save()
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
        
        # Test again
        auth_user = authenticate(username=username, password=password)
        return auth_user is not None
        
    except Exception:
        return False

# Auto-run on import
if __name__ != '__main__':
    ensure_admin_exists()

if __name__ == '__main__':
    success = ensure_admin_exists()
    print(f"GUARANTEED ADMIN: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
