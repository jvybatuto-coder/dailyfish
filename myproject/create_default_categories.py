#!/usr/bin/env python
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import FishCategory

def create_default_categories():
    """Create default fish categories if they don't exist"""
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
            print(f"Created category: {category.name}")
            created_count += 1
        else:
            print(f"Category already exists: {category.name}")
    
    print(f"\nTotal categories created: {created_count}")
    print(f"Total categories in database: {FishCategory.objects.count()}")

if __name__ == '__main__':
    create_default_categories()
