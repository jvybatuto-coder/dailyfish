from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from myapp.models import Category

User = get_user_model()

class Command(BaseCommand):
    help = 'Create default categories and admin user'

    def handle(self, *args, **options):
        # Create default categories
        categories = [
            'Bangus (Milkfish)',
            'Tilapia',
            'Galunggong (Round Scad)',
            'Tambakol (Yellowfin Tuna)',
            'Lapu-Lapu (Grouper)',
            'Maya-Maya (Red Snapper)',
            'Tulingan (Frigate Tuna)',
            'Dilis (Anchovy)',
            'Bangus Belly',
            'Fish Fillet'
        ]

        for category_name in categories:
            category, created = Category.objects.get_or_create(name=category_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category_name}'))

        # Create admin user
        email = 'jvyboy@gmail.com'
        if not User.objects.filter(email=email).exists():
            admin_user = User.objects.create_user(
                username='admin',
                email=email,
                first_name='Admin',
                last_name='User',
                password='admin123',
                role='admin_seller',
                phone='+639123456789',
                address='Admin Office, Fish Market'
            )
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {email}'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin user {email} already exists'))

        self.stdout.write(self.style.SUCCESS('Setup completed successfully!'))
