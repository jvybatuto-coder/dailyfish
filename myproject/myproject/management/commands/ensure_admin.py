from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Ensure admin user exists with correct credentials'

    def handle(self, *args, **options):
        username = 'admin'
        password = 'admin'
        email = 'admin@dailyfish.com'
        
        try:
            # Check if user exists
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                # Update password to ensure it's correct
                user.set_password(password)
                user.is_superuser = True
                user.is_staff = True
                user.is_active = True
                user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Admin user "{username}" updated successfully!')
                )
                self.stdout.write(f'Username: {username}')
                self.stdout.write(f'Password: {password}')
                self.stdout.write(f'Email: {email}')
            else:
                # Create new admin user
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Admin user "{username}" created successfully!')
                )
                self.stdout.write(f'Username: {username}')
                self.stdout.write(f'Password: {password}')
                self.stdout.write(f'Email: {email}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error ensuring admin user: {str(e)}')
            )
            logger.error(f'Error in ensure_admin command: {str(e)}')
