from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

class FishCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Fish Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Fish(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(FishCategory, on_delete=models.CASCADE, related_name='fish')
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    stock_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    image = models.ImageField(upload_to='fish_images/', blank=True, null=True)
    image_url = models.URLField(blank=True, help_text="External image URL if no local image")
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Fish"
    
    def __str__(self):
        return self.name
    
    @property
    def stock_status(self):
        if self.stock_kg <= 0:
            return 'out'
        elif self.stock_kg <= 5:
            return 'low'
        else:
            return 'available'
    
    @property
    def display_image(self):
        if self.image:
            return self.image.url
        elif self.image_url:
            return self.image_url
        else:
            return '/static/images/no-image.png'
            
    @property
    def total_sold(self):
        """Calculate total quantity of this fish sold across all completed orders"""
        from django.db.models import Sum, Q
        
        total = self.orderitem_set.filter(
            order__status='completed'
        ).aggregate(
            total_sold=Sum('quantity_kg')
        )['total_sold']
        
        return total or 0
    
    @property
    def average_rating(self):
        """Calculate average rating from order feedback"""
        from django.db.models import Avg, Count, Q
        
        # Get all order items for this fish that have feedback
        ratings = OrderFeedback.objects.filter(
            order__items__fish=self,
            order__status='completed',
            rating__isnull=False
        ).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        
        return {
            'average': round(ratings['avg_rating'] or 0, 1),
            'count': ratings['count'] or 0
        }

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready for Pickup'),
        ('out_for_delivery', 'Out for Delivery'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    payment_method = models.CharField(max_length=10, choices=[('cod', 'Cash on Delivery'), ('gcash', 'GCash')], default='cod')
    delivery_address = models.TextField(blank=True, help_text="Snapshot of delivery address at time of order")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.created_at.strftime('%Y-%m-%d')}"
    
    def calculate_total(self):
        total = sum(item.total_price for item in self.items.all())
        self.total_amount = total
        self.save()
        return total

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    fish = models.ForeignKey(Fish, on_delete=models.CASCADE)
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['order', 'fish']
    
    def __str__(self):
        return f"{self.fish.name} - {self.quantity_kg}kg"
    
    @property
    def total_price(self):
        return self.quantity_kg * self.unit_price

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for {self.user.username}"
    
    def get_total_items(self):
        return sum(item.quantity_kg for item in self.items.all())
    
    def get_total_amount(self):
        return sum(item.total_price for item in self.items.all())
    
    def get_total_with_shipping(self):
        return self.get_total_amount() + Decimal('50.00')

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    fish = models.ForeignKey(Fish, on_delete=models.CASCADE)
    quantity_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['cart', 'fish']
    
    def __str__(self):
        return f"{self.fish.name} - {self.quantity_kg}kg"
    
    @property
    def total_price(self):
        return self.quantity_kg * self.fish.price_per_kg


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    country = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    municipality = models.CharField(max_length=100, blank=True)
    barangay = models.CharField(max_length=100, blank=True)
    details = models.CharField(max_length=255, blank=True)
    lat = models.CharField(max_length=50, blank=True)
    lng = models.CharField(max_length=50, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

    def formatted_address(self):
        parts = [self.details, self.barangay, self.municipality, self.province, self.country]
        return ", ".join([p for p in parts if p])


class Message(models.Model):
    MESSAGE_TYPES = [
        ('general', 'General Question'),
        ('freshness', 'Freshness Inquiry'),
        ('delivery', 'Delivery Time'),
        ('product', 'Product Information'),
        ('other', 'Other'),
    ]
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='general')
    subject = models.CharField(max_length=200)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username} - {self.subject}"


class OrderFeedback(models.Model):
    RATING_CHOICES = [
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='feedback')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='order_feedbacks')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Feedback for Order #{self.order.id} - {self.rating} stars"
