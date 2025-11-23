from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.db import models
from .models import User, Product, Category, Cart, CartItem, Order, OrderItem
from .forms import UserRegistrationForm, ProductForm, CartForm
from decimal import Decimal

def is_admin_seller(user):
    return user.is_authenticated and user.role == 'admin_seller'

def is_buyer(user):
    return user.is_authenticated and user.role == 'buyer'

# Admin/Seller Views
def admin_login(request):
    if request.user.is_authenticated and request.user.role == 'admin_seller':
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        if user and user.role == 'admin_seller':
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')
    
    return render(request, 'admin/admin-login.html')

@login_required
@user_passes_test(is_admin_seller)
def admin_dashboard(request):
    # Super admin can see all products, others only their own
    if request.user.email == 'jvyboy@gmail.com':
        products = Product.objects.all()
        total_sales = Order.objects.filter(status='delivered').aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    else:
        products = Product.objects.filter(seller=request.user)
        total_sales = Order.objects.filter(items__product__seller=request.user, status='delivered').aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    low_stock_products = products.filter(stock_quantity__lte=models.F('low_stock_threshold'))
    recent_orders = Order.objects.filter(items__product__in=products).distinct()[:5]
    
    context = {
        'total_products': products.count(),
        'low_stock_products': low_stock_products.count(),
        'total_sales': total_sales,
        'recent_orders': recent_orders,
    }
    return render(request, 'admin/admin-dashboard.html', context)

@login_required
@user_passes_test(is_admin_seller)
def admin_manage_products(request):
    if request.user.email == 'jvyboy@gmail.com':
        products = Product.objects.all()
    else:
        products = Product.objects.filter(seller=request.user)
    
    categories = Category.objects.all()
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            messages.success(request, 'Product added successfully!')
            return redirect('admin_manage_products')
    else:
        form = ProductForm()
    
    paginator = Paginator(products, 10)
    page = request.GET.get('page')
    products_page = paginator.get_page(page)
    
    context = {
        'products': products_page,
        'form': form,
        'categories': categories,
    }
    return render(request, 'admin/admin-manage-products.html', context)

@login_required
@user_passes_test(is_admin_seller)
def admin_edit_product(request, pk):
    if request.user.email == 'jvyboy@gmail.com':
        product = get_object_or_404(Product, pk=pk)
    else:
        product = get_object_or_404(Product, pk=pk, seller=request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('admin_manage_products')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'admin/admin-edit-product.html', {'form': form, 'product': product})

@login_required
@user_passes_test(is_admin_seller)
def admin_delete_product(request, pk):
    if request.user.email == 'jvyboy@gmail.com':
        product = get_object_or_404(Product, pk=pk)
    else:
        product = get_object_or_404(Product, pk=pk, seller=request.user)
    
    product.delete()
    messages.success(request, 'Product deleted successfully!')
    return redirect('admin_manage_products')

@login_required
@user_passes_test(is_admin_seller)
def admin_orders(request):
    if request.user.email == 'jvyboy@gmail.com':
        orders = Order.objects.all()
    else:
        orders = Order.objects.filter(items__product__seller=request.user).distinct()
    
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders_page = paginator.get_page(page)
    
    return render(request, 'admin/admin-orders.html', {'orders': orders_page})

@login_required
@user_passes_test(is_admin_seller)
def admin_profile(request):
    return render(request, 'admin/admin-profile.html', {'user': request.user})

# Buyer Views
def buyer_login(request):
    if request.user.is_authenticated and request.user.role == 'buyer':
        return redirect('buyer_home')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        if user and user.role == 'buyer':
            login(request, user)
            return redirect('buyer_home')
        else:
            messages.error(request, 'Invalid credentials.')
    
    return render(request, 'buyer/buyer-login.html')

def buyer_signup(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'buyer'
            user.save()
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('buyer_login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'buyer/buyer-signup.html', {'form': form})

@login_required
@user_passes_test(is_buyer)
def buyer_home(request):
    products = Product.objects.filter(status='active', stock_quantity__gt=0)
    categories = Category.objects.all()
    
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search')
    
    if category_filter:
        products = products.filter(category__slug=category_filter)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    products_page = paginator.get_page(page)
    
    context = {
        'products': products_page,
        'categories': categories,
        'selected_category': category_filter,
        'search_query': search_query,
    }
    return render(request, 'buyer/buyer-home.html', context)

@login_required
@user_passes_test(is_buyer)
def buyer_view(request, pk):
    product = get_object_or_404(Product, pk=pk, status='active')
    return render(request, 'buyer/buyer-view.html', {'product': product})

@login_required
@user_passes_test(is_buyer)
def buyer_cart(request):
    cart, created = Cart.objects.get_or_create(buyer=request.user, is_active=True)
    cart_items = cart.items.all()
    
    if request.method == 'POST':
        form = CartForm(request.POST)
        if form.is_valid():
            product_id = form.cleaned_data['product_id']
            quantity_kg = form.cleaned_data['quantity_kg']
            
            product = get_object_or_404(Product, pk=product_id)
            
            if product.stock_quantity < quantity_kg:
                messages.error(request, 'Not enough stock available.')
            else:
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart, product=product,
                    defaults={'quantity_kg': quantity_kg}
                )
                
                if not created:
                    cart_item.quantity_kg += quantity_kg
                    cart_item.save()
                
                messages.success(request, 'Added to cart!')
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'buyer/buyer-cart.html', context)

@login_required
@user_passes_test(is_buyer)
def buyer_checkout(request):
    cart = get_object_or_404(Cart, buyer=request.user, is_active=True)
    cart_items = cart.items.all()
    
    if not cart_items:
        messages.error(request, 'Your cart is empty.')
        return redirect('buyer_cart')
    
    if request.method == 'POST':
        shipping_address = request.POST.get('shipping_address')
        
        if not shipping_address:
            messages.error(request, 'Please provide a shipping address.')
        else:
            # Create order
            order = Order.objects.create(
                buyer=request.user,
                total_amount=cart.total_amount,
                shipping_address=shipping_address,
            )
            
            # Add items to order
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity_kg=cart_item.quantity_kg,
                    price_per_kilo=cart_item.price_per_kilo,
                    subtotal=cart_item.subtotal,
                )
                
                # Update product stock
                product = cart_item.product
                product.stock_quantity -= cart_item.quantity_kg
                product.save()
            
            # Clear cart
            cart_items.delete()
            
            messages.success(request, f'Order {order.order_number} placed successfully!')
            return redirect('buyer_orders')
    
    return render(request, 'buyer/buyer-checkout.html', {'cart': cart})

@login_required
@user_passes_test(is_buyer)
def buyer_orders(request):
    orders = Order.objects.filter(buyer=request.user).order_by('-created_at')
    return render(request, 'buyer/buyer-orders.html', {'orders': orders})

@login_required
@user_passes_test(is_buyer)
def buyer_profile(request):
    return render(request, 'buyer/buyer-profile.html', {'user': request.user})

def logout_view(request):
    logout(request)
    return redirect('buyer_login')
