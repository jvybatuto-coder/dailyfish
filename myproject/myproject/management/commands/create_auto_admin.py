from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Command(BaseCommand):
    help = 'Automatically creates a superuser if it does not exist'

    def handle(self, *args, **options):
        username = 'admin'
        password = 'admin123'
        email = 'admin@dailyfish.com'

        try:
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'Superuser "{username}" already exists.')
                )
                return

            # Validate password strength
            if len(password) < 8:
                raise ValidationError("Password must be at least 8 characters long")

            # Create superuser
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created superuser "{username}" with email "{email}"'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            )
