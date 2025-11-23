from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from datetime import datetime

from .models import Fish, FishCategory
from .models_new import Product, Category, User

logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
@user_passes_test(is_admin)
def admin_products_new(request):
    """Admin products management page - allows admin to manage all products"""
    try:
        # Get all products (admin can see all)
        products = Product.objects.select_related('seller', 'category').all().order_by('-created_at')
        
        # Apply filters
        search_query = request.GET.get('search', '')
        category_filter = request.GET.get('category', '')
        status_filter = request.GET.get('status', '')
        stock_filter = request.GET.get('stock_filter', '')
        
        if search_query:
            products = products.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(seller__username__icontains=search_query)
            )
        
        if category_filter:
            products = products.filter(category_id=category_filter)
        
        if status_filter:
            products = products.filter(status=status_filter)
        
        if stock_filter:
            if stock_filter == 'low_stock':
                products = products.filter(stock_quantity__lte=models.F('low_stock_threshold'), stock_quantity__gt=0)
            elif stock_filter == 'out_of_stock':
                products = products.filter(stock_quantity=0)
            elif stock_filter == 'normal':
                products = products.filter(stock_quantity__gt=models.F('low_stock_threshold'))
        
        # Pagination
        paginator = Paginator(products, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get categories for filter dropdown
        categories = Category.objects.all()
        
        # Calculate statistics
        total_products = products.count()
        low_stock_count = products.filter(stock_quantity__lte=models.F('low_stock_threshold'), stock_quantity__gt=0).count()
        out_of_stock_count = products.filter(stock_quantity=0).count()
        
        context = {
            'products': page_obj,
            'categories': categories,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
            'total_count': total_products,
            'search_query': search_query,
            'category_filter': category_filter,
            'status_filter': status_filter,
            'stock_filter': stock_filter,
            'stats': {
                'total_products': total_products,
                'low_stock_count': low_stock_count,
                'out_of_stock_count': out_of_stock_count,
            }
        }
        
        return render(request, 'admin_products_new.html', context)
        
    except Exception as e:
        logger.error(f'Admin products error: {str(e)}', exc_info=True)
        messages.error(request, f'Error loading products: {str(e)}')
        return render(request, 'admin_products_new.html', {
            'products': Product.objects.none(),
            'categories': Category.objects.all(),
            'error': True
        })

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_product_add_new(request):
    """Add new product (admin can add products)"""
    try:
        # Get form data
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        price_per_kilo = request.POST.get('price_per_kilo')
        stock_quantity = request.POST.get('stock_quantity')
        description = request.POST.get('description', '')
        low_stock_threshold = request.POST.get('low_stock_threshold', '5')
        status = request.POST.get('status', 'active')
        
        # Validate required fields
        if not all([name, category_id, price_per_kilo, stock_quantity]):
            return JsonResponse({
                'success': False,
                'error': 'Name, category, price, and stock are required'
            })
        
        # Validate numeric fields
        try:
            price_per_kilo = float(price_per_kilo)
            stock_quantity = float(stock_quantity)
            low_stock_threshold = float(low_stock_threshold)
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Price and stock must be valid numbers'
            })
        
        if price_per_kilo <= 0 or stock_quantity < 0:
            return JsonResponse({
                'success': False,
                'error': 'Price must be positive and stock cannot be negative'
            })
        
        # Get category
        category = get_object_or_404(Category, id=category_id)
        
        # Handle image upload
        image = request.FILES.get('image')
        
        # Create product (admin as seller)
        product = Product.objects.create(
            seller=request.user,  # Admin is the seller
            category=category,
            name=name,
            description=description,
            price_per_kilo=price_per_kilo,
            stock_quantity=stock_quantity,
            low_stock_threshold=low_stock_threshold,
            status=status,
            image=image
        )
        
        logger.info(f'Admin {request.user.username} created product: {product.name}')
        
        return JsonResponse({
            'success': True,
            'message': 'Product created successfully',
            'product': {
                'id': product.id,
                'name': product.name,
                'price_per_kilo': str(product.price_per_kilo),
                'stock_quantity': product.stock_quantity,
                'status': product.status,
                'image_url': product.image_url
            }
        })
        
    except Exception as e:
        logger.error(f'Admin product add error: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_product_edit_new(request, product_id):
    """Edit product (admin can edit any product)"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Get form data
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        price_per_kilo = request.POST.get('price_per_kilo')
        stock_quantity = request.POST.get('stock_quantity')
        description = request.POST.get('description', '')
        low_stock_threshold = request.POST.get('low_stock_threshold', '5')
        status = request.POST.get('status', 'active')
        
        # Validate required fields
        if not all([name, category_id, price_per_kilo, stock_quantity]):
            return JsonResponse({
                'success': False,
                'error': 'Name, category, price, and stock are required'
            })
        
        # Validate numeric fields
        try:
            price_per_kilo = float(price_per_kilo)
            stock_quantity = float(stock_quantity)
            low_stock_threshold = float(low_stock_threshold)
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Price and stock must be valid numbers'
            })
        
        if price_per_kilo <= 0 or stock_quantity < 0:
            return JsonResponse({
                'success': False,
                'error': 'Price must be positive and stock cannot be negative'
            })
        
        # Get category
        category = get_object_or_404(Category, id=category_id)
        
        # Handle image upload
        image = request.FILES.get('image')
        
        # Update product
        product.name = name
        product.category = category
        product.description = description
        product.price_per_kilo = price_per_kilo
        product.stock_quantity = stock_quantity
        product.low_stock_threshold = low_stock_threshold
        product.status = status
        
        if image:
            product.image = image
        
        product.save()
        
        logger.info(f'Admin {request.user.username} updated product: {product.name}')
        
        return JsonResponse({
            'success': True,
            'message': 'Product updated successfully',
            'product': {
                'id': product.id,
                'name': product.name,
                'price_per_kilo': str(product.price_per_kilo),
                'stock_quantity': product.stock_quantity,
                'status': product.status,
                'image_url': product.image_url
            }
        })
        
    except Exception as e:
        logger.error(f'Admin product edit error: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_product_delete_new(request, product_id):
    """Delete product (admin can delete any product)"""
    try:
        product = get_object_or_404(Product, id=product_id)
        product_name = product.name
        
        product.delete()
        
        logger.info(f'Admin {request.user.username} deleted product: {product_name}')
        
        return JsonResponse({
            'success': True,
            'message': 'Product deleted successfully'
        })
        
    except Exception as e:
        logger.error(f'Admin product delete error: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@user_passes_test(is_admin)
@require_POST
def admin_product_toggle_status_new(request, product_id):
    """Toggle product status (admin can toggle any product)"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # Toggle status
        if product.status == 'active':
            product.status = 'inactive'
        else:
            product.status = 'active'
        
        product.save()
        
        logger.info(f'Admin {request.user.username} toggled status for product: {product.name} to {product.status}')
        
        return JsonResponse({
            'success': True,
            'message': f'Product status changed to {product.status}',
            'new_status': product.status
        })
        
    except Exception as e:
        logger.error(f'Admin product toggle status error: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@user_passes_test(is_admin)
def admin_product_get_new(request, product_id):
    """Get product details for editing (admin can get any product)"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        return JsonResponse({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'category': product.category.id,
                'category_name': product.category.name,
                'price_per_kilo': str(product.price_per_kilo),
                'stock_quantity': product.stock_quantity,
                'description': product.description,
                'low_stock_threshold': product.low_stock_threshold,
                'status': product.status,
                'image_url': product.image_url,
                'seller_name': product.seller.username,
                'created_at': product.created_at.isoformat(),
                'updated_at': product.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'Admin product get error: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
@user_passes_test(is_admin)
def admin_products_export_csv(request):
    """Export products to CSV (admin can export all products)"""
    try:
        import csv
        from django.http import HttpResponse
        
        # Get all products
        products = Product.objects.select_related('seller', 'category').all()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Name', 'Category', 'Seller', 'Price per Kilo', 
            'Stock Quantity', 'Low Stock Threshold', 'Status', 
            'Description', 'Created At', 'Updated At'
        ])
        
        for product in products:
            writer.writerow([
                product.id,
                product.name,
                product.category.name,
                product.seller.username,
                product.price_per_kilo,
                product.stock_quantity,
                product.low_stock_threshold,
                product.status,
                product.description,
                product.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                product.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        logger.info(f'Admin {request.user.username} exported {products.count()} products to CSV')
        
        return response
        
    except Exception as e:
        logger.error(f'Admin products export error: {str(e)}', exc_info=True)
        messages.error(request, f'Error exporting products: {str(e)}')
        return redirect('admin_products_new')
