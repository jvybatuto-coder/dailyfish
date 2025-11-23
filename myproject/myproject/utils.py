import os
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.conf import settings

def create_superuser_if_not_exists():
    """
    Automatically creates a superuser if it doesn't exist.
    This function is designed to be called during Django startup.
    """
    if not getattr(settings, 'AUTO_CREATE_SUPERUSER', False):
        return
    
    username = 'admin'
    password = 'admin123'
    email = 'admin@dailyfish.com'
    
    try:
        # Check if superuser already exists
        if User.objects.filter(username=username).exists():
            print(f"[INFO] Superuser '{username}' already exists.")
            return
        
        # Validate password strength
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        
        # Create the superuser
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        
        print(f"[SUCCESS] Superuser '{username}' created successfully!")
        print(f"[INFO] Username: {username}")
        print(f"[INFO] Email: {email}")
        print(f"[WARNING] Remember to change the default password in production!")
        
    except Exception as e:
        print(f"[ERROR] Failed to create superuser: {str(e)}")
