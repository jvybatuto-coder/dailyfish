from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models_new import Category, Product, Order, OrderItem, Cart, CartItem, Message, Feedback, ActivityLog

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone', 'address', 'is_active', 'created_at', 'last_login']
        read_only_fields = ['id', 'created_at', 'last_login']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

class ProductSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source='seller.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    image_url = serializers.CharField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'seller', 'seller_name', 'category', 'category_name', 'name', 'slug',
            'description', 'price_per_kilo', 'stock_quantity', 'image', 'image_url',
            'default_image_used', 'status', 'is_active', 'low_stock_threshold',
            'is_low_stock', 'is_out_of_stock', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'seller', 'created_at', 'updated_at']
    
    def validate_image(self, value):
        if value:
            # Validate file size (5MB max)
            max_size = 5 * 1024 * 1024
            if value.size > max_size:
                raise serializers.ValidationError("Image size should not exceed 5MB.")
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/webp']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("Only JPEG, PNG, and WebP images are allowed.")
        
        return value

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity_kg', 'price_per_kilo', 'subtotal']

class OrderSerializer(serializers.ModelSerializer):
    buyer_name = serializers.CharField(source='buyer.username', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'buyer', 'buyer_name', 'order_number', 'status', 'total_amount',
            'shipping_address', 'notes', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'order_number', 'buyer', 'created_at', 'updated_at']

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price_per_kilo', read_only=True, max_digits=10, decimal_places=2)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'quantity_kg', 'price_per_kilo', 'subtotal', 'added_at']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'buyer', 'is_active', 'last_updated', 'items', 'total_amount', 'item_count', 'created_at']
        read_only_fields = ['id', 'buyer', 'created_at']
    
    def get_total_amount(self, obj):
        return obj.total_amount
    
    def get_item_count(self, obj):
        return obj.item_count

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    recipient_name = serializers.CharField(source='recipient.username', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_name', 'recipient', 'recipient_name', 'subject', 'body', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at']

class FeedbackSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Feedback
        fields = [
            'id', 'user', 'user_name', 'product', 'product_name', 'order', 'order_number',
            'message', 'status', 'admin_response', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'user_name', 'action', 'content_type', 'object_id', 'object_repr', 'description', 'ip_address', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

class DashboardStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    total_sellers = serializers.IntegerField()
    total_buyers = serializers.IntegerField()
    total_products = serializers.IntegerField()
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    low_stock_products = serializers.IntegerField()
    out_of_stock_products = serializers.IntegerField()
    unread_messages = serializers.IntegerField()
    pending_feedback = serializers.IntegerField()
    recent_orders = OrderSerializer(many=True)
    top_products = ProductSerializer(many=True)
    recent_activities = ActivityLogSerializer(many=True)
