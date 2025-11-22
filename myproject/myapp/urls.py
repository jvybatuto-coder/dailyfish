from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path('', views.landing_page, name='home'),
    path('marketplace/', views.home, name='marketplace'),
    path('dashboard/', views.buyer_dashboard, name='buyer_dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('location/select/', views.location_select, name='location_select'),
    path('fish/', views.fish_list, name='fish_list'),
    path('fish/<int:fish_id>/', views.fish_detail, name='fish_detail'),
    path('fish/<int:fish_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:fish_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_history, name='order_history'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/data/', views.user_orders_data, name='user_orders_data'),
    path('orders/now/', views.order_now, name='order_now'),
    
    # Seller / Admin Panel (DailyFish)
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/products/', views.seller_products, name='seller_products'),
    path('seller/products/new/', views.seller_product_create, name='seller_product_create'),
    path('seller/products/<int:fish_id>/edit/', views.seller_product_edit, name='seller_product_edit'),
    path('seller/products/<int:fish_id>/delete/', views.seller_product_delete, name='seller_product_delete'),
    path('seller/orders/', views.seller_orders, name='seller_orders'),
    path('seller/profile/', views.seller_profile, name='seller_profile'),

    # Admin Panel (custom)
    path('admin-panel/products/', views.admin_products, name='admin_products'),
   path('admin-panel/products/<int:fish_id>/', views.admin_products, name='admin_product_edit'),
    path('admin-panel/orders/', views.admin_orders, name='admin_orders'),
    path('admin-panel/orders/data/', views.admin_orders_data, name='admin_orders_data'),
    
    # Messaging System URLs
    path('messages/', views.message_center, name='message_center'),
    path('messages/send/', views.send_message, name='send_message'),
    path('messages/<int:message_id>/', views.view_message, name='view_message'),
    path('messages/<int:message_id>/reply/', views.reply_message, name='reply_message'),
    path('orders/<int:order_id>/feedback/', views.order_feedback, name='order_feedback'),
]


