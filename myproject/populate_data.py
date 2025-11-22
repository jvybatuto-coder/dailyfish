#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import FishCategory, Fish

# Create fish categories
categories_data = [
    {'name': 'Freshwater Fish', 'description': 'Fish from freshwater sources like rivers and lakes'},
    {'name': 'Saltwater Fish', 'description': 'Fish from saltwater sources like oceans and seas'},
    {'name': 'Shellfish', 'description': 'Crustaceans and mollusks'},
    {'name': 'Premium Fish', 'description': 'High-quality, premium fish varieties'},
]

categories = {}
for cat_data in categories_data:
    category, created = FishCategory.objects.get_or_create(
        name=cat_data['name'],
        defaults={'description': cat_data['description']}
    )
    categories[cat_data['name']] = category
    print(f"{'Created' if created else 'Found'} category: {category.name}")

# Create fish items
fish_data = [
    {
        'name': 'Salmon',
        'description': 'Fresh Atlantic salmon, perfect for grilling or baking. Rich in omega-3 fatty acids.',
        'category': 'Saltwater Fish',
        'price_per_kg': 450.00,
        'stock_kg': 25.5,
        'image_url': 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=400&h=300&fit=crop'
    },
    {
        'name': 'Tuna',
        'description': 'Premium yellowfin tuna, excellent for sashimi and grilling.',
        'category': 'Saltwater Fish',
        'price_per_kg': 680.00,
        'stock_kg': 18.0,
        'image_url': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400&h=300&fit=crop'
    },
    {
        'name': 'Tilapia',
        'description': 'Fresh tilapia fillets, mild flavor perfect for any cooking method.',
        'category': 'Freshwater Fish',
        'price_per_kg': 280.00,
        'stock_kg': 35.0,
        'image_url': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop'
    },
    {
        'name': 'Bangus (Milkfish)',
        'description': 'Traditional Filipino milkfish, perfect for grilling or frying.',
        'category': 'Saltwater Fish',
        'price_per_kg': 320.00,
        'stock_kg': 22.5,
        'image_url': 'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400&h=300&fit=crop'
    },
    {
        'name': 'Prawns',
        'description': 'Large fresh prawns, perfect for grilling, steaming, or stir-frying.',
        'category': 'Shellfish',
        'price_per_kg': 520.00,
        'stock_kg': 15.0,
        'image_url': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400&h=300&fit=crop'
    },
    {
        'name': 'Crab',
        'description': 'Fresh blue crab, excellent for steaming or making crab cakes.',
        'category': 'Shellfish',
        'price_per_kg': 480.00,
        'stock_kg': 12.0,
        'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=300&fit=crop'
    },
    {
        'name': 'Sea Bass',
        'description': 'Premium sea bass fillets, delicate flavor perfect for fine dining.',
        'category': 'Premium Fish',
        'price_per_kg': 750.00,
        'stock_kg': 8.5,
        'image_url': 'https://images.unsplash.com/photo-1574781330855-d0db72b8e6b3?w=400&h=300&fit=crop'
    },
    {
        'name': 'Red Snapper',
        'description': 'Fresh red snapper, excellent for whole fish cooking or fillets.',
        'category': 'Saltwater Fish',
        'price_per_kg': 420.00,
        'stock_kg': 20.0,
        'image_url': 'https://images.unsplash.com/photo-1574781330855-d0db72b8e6b3?w=400&h=300&fit=crop'
    },
    {
        'name': 'Catfish',
        'description': 'Fresh catfish fillets, perfect for frying or grilling.',
        'category': 'Freshwater Fish',
        'price_per_kg': 250.00,
        'stock_kg': 30.0,
        'image_url': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop'
    },
    {
        'name': 'Lobster',
        'description': 'Premium live lobster, perfect for special occasions.',
        'category': 'Premium Fish',
        'price_per_kg': 1200.00,
        'stock_kg': 5.0,
        'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=300&fit=crop'
    },
    {
        'name': 'Mussels',
        'description': 'Fresh mussels, perfect for steaming with white wine and garlic.',
        'category': 'Shellfish',
        'price_per_kg': 180.00,
        'stock_kg': 25.0,
        'image_url': 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?w=400&h=300&fit=crop'
    },
    {
        'name': 'Mahi Mahi',
        'description': 'Fresh mahi mahi fillets, firm texture perfect for grilling.',
        'category': 'Saltwater Fish',
        'price_per_kg': 550.00,
        'stock_kg': 16.0,
        'image_url': 'https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400&h=300&fit=crop'
    }
]

for fish_info in fish_data:
    fish, created = Fish.objects.get_or_create(
        name=fish_info['name'],
        defaults={
            'description': fish_info['description'],
            'category': categories[fish_info['category']],
            'price_per_kg': fish_info['price_per_kg'],
            'stock_kg': fish_info['stock_kg'],
            'image_url': fish_info['image_url'],
            'is_available': True
        }
    )
    print(f"{'Created' if created else 'Found'} fish: {fish.name}")

print("\nSample data populated successfully!")
print(f"Total categories: {FishCategory.objects.count()}")
print(f"Total fish items: {Fish.objects.count()}")
