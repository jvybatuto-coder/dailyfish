from django.urls import path
from . import views

urlpatterns = [
    # Admin/Seller URLs
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/products/', views.admin_manage_products, name='admin_manage_products'),
    path('admin/products/<int:pk>/edit/', views.admin_edit_product, name='admin_edit_product'),
    path('admin/products/<int:pk>/delete/', views.admin_delete_product, name='admin_delete_product'),
    path('admin/orders/', views.admin_orders, name='admin_orders'),
    path('admin/profile/', views.admin_profile, name='admin_profile'),
    
    # Buyer URLs
    path('buyer/login/', views.buyer_login, name='buyer_login'),
    path('buyer/signup/', views.buyer_signup, name='buyer_signup'),
    path('buyer/home/', views.buyer_home, name='buyer_home'),
    path('buyer/product/<int:pk>/', views.buyer_view, name='buyer_view'),
    path('buyer/cart/', views.buyer_cart, name='buyer_cart'),
    path('buyer/checkout/', views.buyer_checkout, name='buyer_checkout'),
    path('buyer/orders/', views.buyer_orders, name='buyer_orders'),
    path('buyer/profile/', views.buyer_profile, name='buyer_profile'),
    
    # Common URLs
    path('logout/', views.logout_view, name='logout'),
    
    # Default redirect
    path('', views.buyer_home, name='home'),
]
