from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from .models import User
import logging

logger = logging.getLogger(__name__)

@receiver(post_migrate)
def create_superuser_on_migrate(sender, **kwargs):
    """
    Automatically create superuser when migrations run
    This ensures admin access is always available
    """
    if sender.name == 'auth':
        username = 'admin'
        password = 'admin'
        email = 'admin@dailyfish.com'
        
        try:
            # Check if superuser already exists
            if User.objects.filter(username=username).exists():
                logger.info(f"Superuser '{username}' already exists")
                # Update password to ensure it matches
                user = User.objects.get(username=username)
                user.set_password(password)
                user.save()
                logger.info(f"Updated password for existing superuser '{username}'")
            else:
                # Create new superuser
                User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                logger.info(f"Created superuser '{username}' successfully")
                
        except Exception as e:
            logger.error(f"Error creating superuser: {str(e)}")
            # Don't raise exception to avoid breaking migrations
