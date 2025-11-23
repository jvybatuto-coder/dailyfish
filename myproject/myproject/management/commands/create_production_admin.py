from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth import authenticate

class Command(BaseCommand):
    help = 'Create admin user for production deployment'

    def handle(self, *args, **options):
        username = 'admin'
        password = 'admin'
        email = 'admin@dailyfish.com'
        
        try:
            # Check if user exists
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                user.set_password(password)
                user.is_superuser = True
                user.is_staff = True
                user.is_active = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated existing admin user "{username}"')
                )
            else:
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created new admin user "{username}"')
                )
            
            # Test authentication
            auth_user = authenticate(username=username, password=password)
            if auth_user:
                self.stdout.write(
                    self.style.SUCCESS('Authentication test PASSED')
                )
                self.stdout.write(f'Username: {username}')
                self.stdout.write(f'Password: {password}')
            else:
                self.stdout.write(
                    self.style.ERROR('Authentication test FAILED')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
