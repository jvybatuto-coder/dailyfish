from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from decimal import Decimal
import random
from datetime import datetime, timedelta

from myapp.models_new import Category, Product, OrderNew, OrderItemNew, CartNew, CartItemNew, MessageNew, Feedback, ActivityLog

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Starting database seeding...')
        
        # Create users
        self.create_users()
        
        # Create categories
        self.create_categories()
        
        # Create products
        self.create_products()
        
        # Create orders
        self.create_orders()
        
        # Create messages
        self.create_messages()
        
        # Create feedback
        self.create_feedback()
        
        # Create activity logs
        self.create_activity_logs()
        
        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))

    def create_users(self):
        self.stdout.write('Creating users...')
        
        # Admin user
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@dailyfish.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
        
        # Sellers
        sellers_data = [
            {'username': 'seller1', 'email': 'seller1@dailyfish.com', 'first_name': 'Juan', 'last_name': 'Santos'},
            {'username': 'seller2', 'email': 'seller2@dailyfish.com', 'first_name': 'Maria', 'last_name': 'Reyes'},
            {'username': 'seller3', 'email': 'seller3@dailyfish.com', 'first_name': 'Carlos', 'last_name': 'Garcia'},
        ]
        
        for seller_data in sellers_data:
            seller, created = User.objects.get_or_create(
                username=seller_data['username'],
                defaults={
                    **seller_data,
                    'role': 'seller',
                    'is_staff': False,
                }
            )
            if created:
                seller.set_password('seller123')
                seller.save()
        
        # Buyers
        buyers_data = [
            {'username': 'buyer1', 'email': 'buyer1@dailyfish.com', 'first_name': 'Ana', 'last_name': 'Diaz'},
            {'username': 'buyer2', 'email': 'buyer2@dailyfish.com', 'first_name': 'Jose', 'last_name': 'Martinez'},
            {'username': 'buyer3', 'email': 'buyer3@dailyfish.com', 'first_name': 'Sofia', 'last_name': 'Lopez'},
            {'username': 'buyer4', 'email': 'buyer4@dailyfish.com', 'first_name': 'Miguel', 'last_name': 'Hernandez'},
            {'username': 'buyer5', 'email': 'buyer5@dailyfish.com', 'first_name': 'Isabella', 'last_name': 'Cruz'},
        ]
        
        for buyer_data in buyers_data:
            buyer, created = User.objects.get_or_create(
                username=buyer_data['username'],
                defaults={
                    **buyer_data,
                    'role': 'buyer',
                    'is_staff': False,
                }
            )
            if created:
                buyer.set_password('buyer123')
                buyer.save()

    def create_categories(self):
        self.stdout.write('Creating categories...')
        
        categories_data = [
            {'name': 'Bangus (Milkfish)', 'description': 'Fresh milkfish from local farms'},
            {'name': 'Tilapia', 'description': 'Farm-raised tilapia'},
            {'name': 'Galunggong (Round Scad)', 'description': 'Popular local fish'},
            {'name': 'Tamban (Sardines)', 'description': 'Fresh sardines'},
            {'name': 'Lapu-Lapu (Grouper)', 'description': 'Premium grouper fish'},
            {'name': 'Maya-Maya (Red Snapper)', 'description': 'Delicious red snapper'},
            {'name': 'Tanguingue (Spanish Mackerel)', 'description': 'Spanish mackerel'},
            {'name': 'Bangus Belly', 'description': 'Milkfish belly cuts'},
            {'name': 'Shrimp', 'description': 'Fresh local shrimp'},
            {'name': 'Squid', 'description': 'Fresh squid'},
        ]
        
        for cat_data in categories_data:
            Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )

    def create_products(self):
        self.stdout.write('Creating products...')
        
        sellers = User.objects.filter(role='seller')
        categories = list(Category.objects.all())
        
        products_data = [
            {'name': 'Fresh Bangus Large', 'price': Decimal('120.00'), 'stock': 50, 'category_idx': 0},
            {'name': 'Fresh Bangus Medium', 'price': Decimal('100.00'), 'stock': 30, 'category_idx': 0},
            {'name': 'Premium Tilapia', 'price': Decimal('80.00'), 'stock': 100, 'category_idx': 1},
            {'name': 'Fresh Galunggong', 'price': Decimal('60.00'), 'stock': 200, 'category_idx': 2},
            {'name': 'Large Tamban', 'price': Decimal('40.00'), 'stock': 150, 'category_idx': 3},
            {'name': 'Premium Lapu-Lapu', 'price': Decimal('350.00'), 'stock': 15, 'category_idx': 4},
            {'name': 'Fresh Maya-Maya', 'price': Decimal('280.00'), 'stock': 20, 'category_idx': 5},
            {'name': 'Tanguingue Fillet', 'price': Decimal('200.00'), 'stock': 25, 'category_idx': 6},
            {'name': 'Bangus Belly Marinated', 'price': Decimal('150.00'), 'stock': 35, 'category_idx': 7},
            {'name': 'Large Shrimp', 'price': Decimal('400.00'), 'stock': 10, 'category_idx': 8},
            {'name': 'Medium Shrimp', 'price': Decimal('300.00'), 'stock': 40, 'category_idx': 8},
            {'name': 'Fresh Squid', 'price': Decimal('250.00'), 'stock': 30, 'category_idx': 9},
            {'name': 'Bangus Smoked', 'price': Decimal('180.00'), 'stock': 25, 'category_idx': 0},
            {'name': 'Tilapia Fillet', 'price': Decimal('120.00'), 'stock': 60, 'category_idx': 1},
            {'name': 'Galunggong Fried', 'price': Decimal('75.00'), 'stock': 80, 'category_idx': 2},
        ]
        
        for product_data in products_data:
            seller = random.choice(sellers)
            category = categories[product_data['category_idx']]
            
            Product.objects.get_or_create(
                name=product_data['name'],
                seller=seller,
                defaults={
                    'category': category,
                    'price_per_kilo': product_data['price'],
                    'stock_quantity': product_data['stock'],
                    'description': f'High-quality {product_data["name"]} sourced from local suppliers.',
                    'low_stock_threshold': random.choice([5, 10, 15]),
                }
            )

    def create_orders(self):
        self.stdout.write('Creating orders...')
        
        buyers = User.objects.filter(role='buyer')
        products = list(Product.objects.filter(is_active=True))
        
        if not buyers or not products:
            return
        
        for i in range(20):
            buyer = random.choice(buyers)
            
            # Create order
            order = OrderNew.objects.create(
                buyer=buyer,
                total_amount=Decimal('0.00'),
                shipping_address=f'{random.randint(100, 999)} {random.choice(["Main St", "Oak Ave", "Elm St"])} {random.choice(["Manila", "Quezon City", "Makati"])}, Philippines',
                status=random.choice(['pending', 'processing', 'shipped', 'delivered']),
                created_at=datetime.now() - timedelta(days=random.randint(1, 30))
            )
            
            # Add random items to order
            num_items = random.randint(1, 3)
            selected_products = random.sample(products, min(num_items, len(products)))
            total = Decimal('0.00')
            
            for product in selected_products:
                quantity = Decimal(str(round(random.uniform(0.5, 5.0), 2)))
                subtotal = quantity * product.price_per_kilo
                total += subtotal
                
                OrderItemNew.objects.create(
                    order=order,
                    product=product,
                    quantity_kg=quantity,
                    price_per_kilo=product.price_per_kilo,
                    subtotal=subtotal
                )
            
            order.total_amount = total
            order.save()

    def create_messages(self):
        self.stdout.write('Creating messages...')
        
        users = list(User.objects.all())
        admin = User.objects.get(username='admin')
        
        messages_data = [
            {'subject': 'Welcome to DailyFish!', 'body': 'Thank you for joining our platform. If you have any questions, feel free to reach out.'},
            {'subject': 'Order Confirmation', 'body': 'Your order has been confirmed and is being processed.'},
            {'subject': 'Payment Received', 'body': 'We have received your payment. Your order will be shipped soon.'},
            {'subject': 'Product Inquiry', 'body': 'I would like to inquire about the availability of fresh bangus.'},
            {'subject': 'Shipping Update', 'body': 'Your order has been shipped and will arrive within 2-3 business days.'},
        ]
        
        for i in range(15):
            sender = random.choice(users)
            recipient = random.choice([u for u in users if u != sender])
            message_data = random.choice(messages_data)
            
            MessageNew.objects.get_or_create(
                sender=sender,
                recipient=recipient,
                subject=message_data['subject'],
                defaults={
                    'body': message_data['body'],
                    'is_read': random.choice([True, False]),
                    'created_at=datetime.now() - timedelta(hours=random.randint(1, 72))
                }
            )

    def create_feedback(self):
        self.stdout.write('Creating feedback...')
        
        buyers = User.objects.filter(role='buyer')
        products = list(Product.objects.all())
        orders = list(OrderNew.objects.all())
        
        feedback_messages = [
            'Excellent quality fish! Very fresh and well-packaged.',
            'Fast delivery and great customer service.',
            'Products are always fresh. Highly recommended!',
            'Good prices and quality products.',
            'Very satisfied with my purchase. Will order again.',
            'Fish was fresh but packaging could be improved.',
            'Great variety of products available.',
            'Delivery was a bit delayed but products were worth the wait.',
        ]
        
        for i in range(25):
            user = random.choice(buyers)
            
            # Randomly choose to associate with product or order
            if random.choice([True, False]) and products:
                product = random.choice(products)
                order = None
            elif orders:
                order = random.choice(orders)
                product = None
            else:
                continue
            
            Feedback.objects.get_or_create(
                user=user,
                product=product,
                order=order,
                defaults={
                    'message': random.choice(feedback_messages),
                    'status': random.choice(['pending', 'handled', 'resolved']),
                    'admin_response': random.choice(['Thank you for your feedback!', 'We appreciate your input.', 'Your feedback helps us improve.'] if random.random() > 0.5 else ''),
                    'created_at=datetime.now() - timedelta(days=random.randint(1, 60))
                }
            )

    def create_activity_logs(self):
        self.stdout.write('Creating activity logs...')
        
        users = list(User.objects.all())
        actions = ['create', 'update', 'delete', 'login', 'logout']
        content_types = ['product', 'order', 'user', 'category', 'message']
        
        for i in range(100):
            user = random.choice(users)
            action = random.choice(actions)
            content_type = random.choice(content_types)
            
            descriptions = {
                'create': f'Created new {content_type}',
                'update': f'Updated {content_type} information',
                'delete': f'Deleted {content_type}',
                'login': 'User logged in',
                'logout': 'User logged out'
            }
            
            ActivityLog.objects.create(
                user=user,
                action=action,
                content_type=content_type,
                object_id=random.randint(1, 100),
                object_repr=f'{content_type.title()} #{random.randint(1, 100)}',
                description=descriptions[action],
                ip_address=f'192.168.1.{random.randint(1, 254)}',
                created_at=datetime.now() - timedelta(hours=random.randint(1, 168))
            )
