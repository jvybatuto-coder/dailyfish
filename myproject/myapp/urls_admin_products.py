from django.urls import path
from . import views_admin_products

app_name = 'admin_products'

urlpatterns = [
    path('', views_admin_products.admin_products_new, name='list'),
    path('add/', views_admin_products.admin_product_add_new, name='add'),
    path('edit/<int:product_id>/', views_admin_products.admin_product_edit_new, name='edit'),
    path('delete/<int:product_id>/', views_admin_products.admin_product_delete_new, name='delete'),
    path('toggle/<int:product_id>/', views_admin_products.admin_product_toggle_status_new, name='toggle'),
    path('get/<int:product_id>/', views_admin_products.admin_product_get_new, name='get'),
    path('export/', views_admin_products.admin_products_export_csv, name='export'),
]
