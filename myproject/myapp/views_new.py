from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models_new import Category, Product, Order, OrderItem, Cart, CartItem, Message, Feedback, ActivityLog
from .serializers_new import (
    UserSerializer, CategorySerializer, ProductSerializer, OrderSerializer,
    CartSerializer, CartItemSerializer, MessageSerializer, FeedbackSerializer,
    ActivityLogSerializer, DashboardStatsSerializer
)
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.seller == request.user or request.user.is_staff

class IsBuyerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.buyer == request.user or request.user.is_staff

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'username', 'email']
    ordering = ['-created_at']

    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action='update',
            content_type='user',
            object_id=user.id,
            object_repr=str(user),
            description=f"{'Activated' if user.is_active else 'Deactivated'} user {user.username}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({'status': 'success', 'is_active': user.is_active})

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def perform_create(self, serializer):
        category = serializer.save()
        ActivityLog.objects.create(
            user=self.request.user,
            action='create',
            content_type='category',
            object_id=category.id,
            object_repr=str(category),
            description=f"Created category {category.name}",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_update(self, serializer):
        category = serializer.save()
        ActivityLog.objects.create(
            user=self.request.user,
            action='update',
            content_type='category',
            object_id=category.id,
            object_repr=str(category),
            description=f"Updated category {category.name}",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        ActivityLog.objects.create(
            user=self.request.user,
            action='delete',
            content_type='category',
            object_id=instance.id,
            object_repr=str(instance),
            description=f"Deleted category {instance.name}",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'status', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price_per_kilo', 'stock_quantity', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Product.objects.select_related('seller', 'category').all()
        elif user.role == 'seller':
            return Product.objects.select_related('seller', 'category').filter(seller=user)
        else:
            return Product.objects.select_related('seller', 'category').filter(is_active=True, status='active')

    def perform_create(self, serializer):
        if self.request.user.role != 'seller' and not self.request.user.is_staff:
            raise permissions.PermissionDenied("Only sellers can create products.")
        
        product = serializer.save(seller=self.request.user)
        ActivityLog.objects.create(
            user=self.request.user,
            action='create',
            content_type='product',
            object_id=product.id,
            object_repr=str(product),
            description=f"Created product {product.name}",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_update(self, serializer):
        product = self.get_object()
        if product.seller != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("You can only edit your own products.")
        
        updated_product = serializer.save()
        ActivityLog.objects.create(
            user=self.request.user,
            action='update',
            content_type='product',
            object_id=updated_product.id,
            object_repr=str(updated_product),
            description=f"Updated product {updated_product.name}",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        if instance.seller != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("You can only delete your own products.")
        
        ActivityLog.objects.create(
            user=self.request.user,
            action='delete',
            content_type='product',
            object_id=instance.id,
            object_repr=str(instance),
            description=f"Deleted product {instance.name}",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get products with low stock"""
        if request.user.role != 'seller' and not request.user.is_staff:
            raise permissions.PermissionDenied("Access denied.")
        
        queryset = self.get_queryset().filter(stock_quantity__lte=models.F('low_stock_threshold'))
        if request.user.role == 'seller':
            queryset = queryset.filter(seller=request.user)
        
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'buyer']
    search_fields = ['order_number', 'buyer__username']
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Order.objects.select_related('buyer').prefetch_related('items__product').all()
        elif user.role == 'buyer':
            return Order.objects.select_related('buyer').prefetch_related('items__product').filter(buyer=user)
        else:
            return Order.objects.none()

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update order status (admin only)"""
        if not request.user.is_staff:
            raise permissions.PermissionDenied("Only admins can update order status.")
        
        order = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Order.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = order.status
        order.status = new_status
        order.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action='order_status',
            content_type='order',
            object_id=order.id,
            object_repr=str(order),
            description=f"Changed order status from {old_status} to {new_status}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({'status': 'success', 'new_status': new_status})

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'buyer':
            return Cart.objects.filter(buyer=self.request.user, is_active=True)
        return Cart.objects.none()

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Add item to cart"""
        if request.user.role != 'buyer':
            raise permissions.PermissionDenied("Only buyers can add items to cart.")
        
        product_id = request.data.get('product_id')
        quantity_kg = request.data.get('quantity_kg')
        
        try:
            product = Product.objects.get(id=product_id, is_active=True, status='active')
            if product.stock_quantity < float(quantity_kg):
                return Response({'error': 'Insufficient stock'}, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response({'error': 'Product not available'}, status=status.HTTP_404_NOT_FOUND)
        
        cart, created = Cart.objects.get_or_create(buyer=request.user, is_active=True)
        
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'quantity_kg': quantity_kg,
                'price_per_kilo': product.price_per_kilo
            }
        )
        
        if not item_created:
            cart_item.quantity_kg += float(quantity_kg)
            cart_item.save()
        
        return Response({'status': 'success', 'message': 'Item added to cart'})

    @action(detail=True, methods=['delete'])
    def clear(self, request, pk=None):
        """Clear cart"""
        cart = self.get_object()
        cart.items.all().delete()
        return Response({'status': 'success', 'message': 'Cart cleared'})

    @action(detail=True, methods=['post'])
    def checkout(self, request, pk=None):
        """Convert cart to order"""
        if request.user.role != 'buyer':
            raise permissions.PermissionDenied("Only buyers can checkout.")
        
        cart = self.get_object()
        if not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        shipping_address = request.data.get('shipping_address')
        if not shipping_address:
            return Response({'error': 'Shipping address required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create order
        order = Order.objects.create(
            buyer=request.user,
            total_amount=cart.total_amount,
            shipping_address=shipping_address
        )
        
        # Create order items
        for cart_item in cart.items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity_kg=cart_item.quantity_kg,
                price_per_kilo=cart_item.price_per_kilo,
                subtotal=cart_item.subtotal
            )
            
            # Update product stock
            product = cart_item.product
            product.stock_quantity -= float(cart_item.quantity_kg)
            product.save()
        
        # Clear cart
        cart.is_active = False
        cart.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action='create',
            content_type='order',
            object_id=order.id,
            object_repr=str(order),
            description=f"Created order {order.order_number}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response(OrderSerializer(order).data)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(
            Q(sender=user) | Q(recipient=user)
        ).select_related('sender', 'recipient')

    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)
        ActivityLog.objects.create(
            user=self.request.user,
            action='create',
            content_type='message',
            object_id=message.id,
            object_repr=str(message),
            description=f"Sent message to {message.recipient.username}",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    @action(detail=True, methods=['patch'])
    def mark_read(self, request, pk=None):
        """Mark message as read"""
        message = self.get_object()
        if message.recipient != request.user:
            raise permissions.PermissionDenied("You can only mark your own messages as read.")
        
        message.is_read = True
        message.save()
        return Response({'status': 'success'})

class FeedbackViewSet(viewsets.ModelViewSet):
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['message', 'user__username']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Feedback.objects.select_related('user', 'product', 'order').all()
        else:
            return Feedback.objects.filter(user=user).select_related('user', 'product', 'order')

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update feedback status (admin only)"""
        if not request.user.is_staff:
            raise permissions.PermissionDenied("Only admins can update feedback status.")
        
        feedback = self.get_object()
        new_status = request.data.get('status')
        admin_response = request.data.get('admin_response', '')
        
        if new_status not in dict(Feedback.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        feedback.status = new_status
        if admin_response:
            feedback.admin_response = admin_response
        feedback.save()
        
        return Response({'status': 'success'})

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """Get dashboard statistics"""
    if not request.user.is_staff:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Basic stats
    total_users = User.objects.count()
    total_sellers = User.objects.filter(role='seller').count()
    total_buyers = User.objects.filter(role='buyer').count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    completed_orders = Order.objects.filter(status='delivered').count()
    total_revenue = Order.objects.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or 0
    low_stock_products = Product.objects.filter(stock_quantity__lte=models.F('low_stock_threshold')).count()
    out_of_stock_products = Product.objects.filter(stock_quantity=0).count()
    unread_messages = Message.objects.filter(recipient=request.user, is_read=False).count()
    pending_feedback = Feedback.objects.filter(status='pending').count()
    
    # Recent data
    recent_orders = Order.objects.select_related('buyer').order_by('-created_at')[:5]
    top_products = Product.objects.annotate(order_count=Count('orderitem')).order_by('-order_count')[:5]
    recent_activities = ActivityLog.objects.select_related('user').order_by('-created_at')[:10]
    
    data = {
        'total_users': total_users,
        'total_sellers': total_sellers,
        'total_buyers': total_buyers,
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'unread_messages': unread_messages,
        'pending_feedback': pending_feedback,
        'recent_orders': OrderSerializer(recent_orders, many=True).data,
        'top_products': ProductSerializer(top_products, many=True).data,
        'recent_activities': ActivityLogSerializer(recent_activities, many=True).data,
    }
    
    return Response(data)
