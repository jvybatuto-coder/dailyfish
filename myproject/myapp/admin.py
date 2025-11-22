from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import FishCategory, Fish, Order, OrderItem, Cart, CartItem, UserProfile

@admin.register(FishCategory)
class FishCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']
    ordering = ['name']

@admin.register(Fish)
class FishAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price_per_kg', 'stock_kg', 'is_available', 'stock_status_badge', 'created_at']
    list_filter = ['category', 'is_available', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price_per_kg', 'stock_kg', 'is_available']
    ordering = ['-created_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category')
        }),
        ('Pricing & Stock', {
            'fields': ('price_per_kg', 'stock_kg', 'is_available')
        }),
        ('Images', {
            'fields': ('image', 'image_url')
        }),
    )

    def stock_status_badge(self, obj):
        status = obj.stock_status
        color = 'red' if status == 'out' else ('orange' if status == 'low' else 'green')
        return mark_safe(f"<span style='padding:2px 8px; border-radius:10px; background:{color}; color:#000;'>{status}</span>")
    stock_status_badge.short_description = 'Stock Status'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total_price']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'total_amount']
    inlines = [OrderItemInline]
    ordering = ['-created_at']
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.calculate_total()

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'fish', 'quantity_kg', 'unit_price', 'total_price']
    list_filter = ['order__status']
    search_fields = ['fish__name', 'order__user__username']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'formatted_address', 'updated_at']
    search_fields = ['user__username', 'user__email', 'barangay', 'municipality', 'province']
    readonly_fields = ['updated_at']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_total_items', 'get_total_amount', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'fish', 'quantity_kg', 'total_price', 'added_at']
    list_filter = ['added_at']
    search_fields = ['fish__name', 'cart__user__username']
