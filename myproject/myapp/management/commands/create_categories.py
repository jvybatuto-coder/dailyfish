from django.core.management.base import BaseCommand
from myapp.models import FishCategory

class Command(BaseCommand):
    help = 'Create default fish categories'

    def handle(self, *args, **options):
        default_categories = [
            {'name': 'Fresh Water Fish', 'description': 'Fish from fresh water sources like rivers and lakes'},
            {'name': 'Salt Water Fish', 'description': 'Fish from salt water sources like seas and oceans'},
            {'name': 'Shellfish', 'description': 'Sea creatures with shells like clams, mussels, and oysters'},
            {'name': 'Crustaceans', 'description': 'Sea creatures with hard shells like crabs, shrimp, and lobsters'},
            {'name': 'Processed Fish', 'description': 'Processed and preserved fish products'},
        ]
        
        created_count = 0
        for cat_data in default_categories:
            category, created = FishCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
                created_count += 1
            else:
                self.stdout.write(f'Category already exists: {category.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal categories created: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'Total categories in database: {FishCategory.objects.count()}'))
