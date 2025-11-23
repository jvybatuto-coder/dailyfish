from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseServerError
from django.db import transaction, IntegrityError, DatabaseError
from django.db.models import Q, Sum, F, Count, Case, When, Value, IntegerField, ProtectedError, Avg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from django.core.validators import validate_email, URLValidator
from django.utils import timezone
from django.utils.timezone import localtime, now
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.cache import never_cache, cache_control
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags, escape
from django.views.decorators.http import condition
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import cache_page
from django.urls import reverse
from django.views.decorators.gzip import gzip_page
from django.core.cache import cache
from django.db.models.functions import Coalesce
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
from django.db import connection
from functools import wraps
import json
import re
import logging
import traceback
from decimal import Decimal, DecimalException, InvalidOperation
import os
import hashlib
from datetime import timedelta
from urllib.parse import urlparse, urljoin

# Security
from django.views.decorators.clickjacking import xframe_options_deny
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_safe
from django.middleware.csrf import get_token

# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
PAGINATION_DEFAULT = 10
PAGINATION_MAX = 100

# Custom exceptions
class DailyFishException(Exception):
    """Base exception for custom exceptions"""
    pass

class InsufficientStock(DailyFishException):
    pass

class PaymentError(DailyFishException):
    pass

def landing_page(request):
    """Landing page view that shows before user logs in."""
    if request.user.is_authenticated:
        # Authenticated users should go to the marketplace
        return redirect('marketplace')
    return render(request, 'landing.html')

# Utility functions
def is_safe_url(url, allowed_hosts=None, require_https=False):
    """Check if URL is safe for redirection"""
    if url is None:
        return False
    
    url = url.strip()
    if not url:
        return False
    
    # Check if URL is relative
    if url.startswith('/'):
        return True
    
    # Check absolute URLs
    if '//' in url:
        try:
            result = urlparse(url)
            if not result.scheme or (require_https and result.scheme != 'https'):
                return False
            if not result.netloc:
                return False
            if allowed_hosts and result.netloc not in allowed_hosts:
                return False
            return True
        except ValueError:
            return False
    return False

def handle_uploaded_file(f, upload_to):
    """Handle file uploads with size and type validation"""
    if f.size > MAX_UPLOAD_SIZE:
        raise ValidationError(f'File size exceeds {MAX_UPLOAD_SIZE/1024/1024}MB limit')
    
    # Validate file extension
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError('Unsupported file type. Please upload an image file.')
    
    # Generate unique filename
    file_hash = hashlib.md5(f.read()).hexdigest()
    filename = f"{file_hash}{ext}"
    filepath = os.path.join(settings.MEDIA_ROOT, upload_to, filename)
    
    # Save file
    with open(filepath, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    
    return os.path.join(upload_to, filename)

from .models import (
    Fish, FishCategory, Cart, CartItem, Order, 
    OrderItem, UserProfile, Message, OrderFeedback
)

# Configure logging
logger = logging.getLogger(__name__)

# Custom decorators
@login_required
@cache_control(public=True, max_age=300)  # Cache for 5 minutes
@vary_on_cookie
def home(request):
    """Home view showing featured fish and categories with caching and error handling.

    Returns:
        HttpResponse: Rendered home page or error page
    """
    cache_key = f'home_page_{request.user.id}'
    cached_response = cache.get(cache_key)

    # Return cached response if available
    if cached_response is not None and not request.GET.get('refresh'):
        return cached_response

    try:
        with transaction.atomic():
            # Get featured fish with related data in a single query
            featured_fish = (
                Fish.objects.select_related('category')
                .filter(is_available=True, stock_kg__gt=0)
                .order_by('-created_at')[:6]
            )

            # Get categories with fish count
            categories = (
                FishCategory.objects.annotate(
                    fish_count=Count(
                        'fish',
                        filter=Q(fish__is_available=True) & Q(fish__stock_kg__gt=0),
                        distinct=True,
                    )
                )
                .filter(fish_count__gt=0)
                .order_by('name')[:4]
            )

            context = {
                'featured_fish': list(featured_fish),  # Force evaluation of queryset
                'categories': list(categories),  # Force evaluation of queryset
                'current_time': timezone.now(),
            }

            # Render template (buyer home) – use existing home.html
            response = render(request, 'home.html', context)

            # Cache the response
            cache.set(cache_key, response, 300)  # Cache for 5 minutes

            return response

    except DatabaseError as e:
        logger.error(f"Database error in home view: {str(e)}\n{traceback.format_exc()}")
        return render(
            request,
            'error.html',
            {'error': 'A database error occurred. Please try again later.'},
            status=500,
        )
    except Exception as e:
        logger.error(f"Unexpected error in home view: {str(e)}\n{traceback.format_exc()}")
        if settings.DEBUG:
            raise  # Re-raise in development for better debugging
        return render(
            request,
            'error.html',
            {'error': 'An unexpected error occurred. Our team has been notified.'},
            status=500,
        )

def validate_password_strength(password, request_post=None):
    """
    Validate password meets security requirements.
    
    Args:
        password (str): The password to validate
        
    Raises:
        ValidationError: If password doesn't meet requirements
    """
    if not isinstance(password, str):
        raise ValidationError("Password must be a string.")
        
    errors = []
    
    # Length check (reduced from 12 to 8 for better user experience)
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")
    
    # Basic complexity checks (simplified from original)
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one number.")
    
    # Check for common passwords
    common_passwords = ['password', '12345678', 'qwerty', 'letmein', 'welcome', '123456789', '1234567']
    if password.lower() in common_passwords:
        errors.append("Password is too common. Please choose a stronger password.")
    
    # Check for sequential characters (slightly relaxed)
    if re.search(r'(.)\1{4,}', password):  # Changed from 3 to 4 repeated chars
        errors.append("Password contains too many repeated characters.")
    
    # Check for personal information in password (kept as is for security)
    user_info = ['username', 'first_name', 'last_name', 'email']
    for field in user_info:
        try:
            if (request_post and field in request_post and 
                request_post[field] and 
                len(request_post[field]) > 3 and  # Only check if field value is long enough
                request_post[field].lower() in password.lower()):
                errors.append("Password should not contain your personal information.")
                break
        except Exception:
            continue
    
    if errors:
        raise ValidationError(errors)
    
    return True

def register_view(request):
    """Handle user registration with validation and error handling - buyers only"""
    if request.method == 'POST':
        try:
            # Get form data with proper type conversion
            raw_username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip().lower()
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')
            
            # Force role to buyer - no seller registration allowed
            role = 'buyer'
            
            # Initialize username early to prevent UnboundLocalError
            username = raw_username
            
            # Validate required fields for buyer registration
            if not all([email, password1, password2, raw_username]):
                raise ValidationError('Please fill in all required fields.')

            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError('Please enter a valid email address.')

            # Enforce Gmail-only registration
            if not email.endswith('@gmail.com'):
                raise ValidationError('Please use a Gmail address (ending in @gmail.com).')
                
            # Validate username (alphanumeric + underscore, 3-30 chars)
            if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
                raise ValidationError(
                    'Username must be 3-30 characters long and contain only letters, numbers, and underscores.'
                )
                
            # Validate password
            if password1 != password2:
                raise ValidationError('Passwords do not match.')
                
            validate_password_strength(password1, request.POST)
            
            # Check if username or email already exists (case-insensitive)
            if User.objects.filter(username__iexact=username).exists():
                raise ValidationError('Username is already taken.')
                
            if User.objects.filter(email__iexact=email).exists():
                raise ValidationError('Email is already registered.')
            
            # Start transaction
            with transaction.atomic():
                # Create buyer user (not staff)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                    is_staff=False
                )
                
                # Create related objects
                Cart.objects.create(user=user)
                profile = UserProfile.objects.create(user=user)

                # Add to buyer group
                group, _ = Group.objects.get_or_create(name='Buyer')
                user.groups.add(group)
                
                # Set role in session
                request.session['user_role'] = role
                
                # Save the session before login to ensure it's persisted
                request.session.save()
                
                # Auto-login after registration
                login(request, user)
                
                # Set session expiry to a reasonable value
                if not request.session.get_expire_at_browser_close():
                    request.session.set_expiry(60 * 60 * 24 * 7)  # 1 week
                
                messages.success(request, f'Welcome, {user.username}! Your account has been created successfully.')
                
                # Redirect to fish list for buyers
                return redirect('fish_list')
                
        except ValidationError as e:
            messages.error(request, str(e))
        except IntegrityError as e:
            logger.error(f'Database error during registration: {str(e)}')
            messages.error(request, 'An error occurred during registration. Please try again.')
        except Exception as e:
            logger.error(f'Unexpected error in registration: {str(e)}', exc_info=True)
            logger.error(f'Form data: username={username if "username" in locals() else "undefined"}, email={email if "email" in locals() else "undefined"}')
            logger.error(f'POST data: {dict(request.POST)}')
            messages.error(request, f'Registration error: {str(e)}')
    
    # Handle GET request or failed POST
    return render(request, 'login.html', {'show_register': True})

@require_http_methods(['GET', 'POST'])
@csrf_protect
def login_view(request):
    """Handle user login with automatic role detection"""
    # Ensure admin exists
    try:
        import guaranteed_admin
        guaranteed_admin.ensure_admin_exists()
    except Exception:
        pass
    
    # Redirect if already authenticated
    if request.user.is_authenticated:
        role = request.session.get('user_role', 'buyer')
        # Admin users go to custom admin dashboard
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        return redirect('fish_list')
    
    if request.method == 'POST':
        try:
            username_input = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            
            # Basic validation
            if not all([username_input, password]):
                raise ValidationError('Please fill in all required fields.')
            
            # Authenticate user with username
            user = authenticate(request, username=username_input, password=password)
            
            if user is None:
                # Log failed login attempt
                logger.warning(f'Failed login attempt for username: {username_input}')
                raise ValidationError('Invalid username or password.')
                
            # Check if user is active
            if not user.is_active:
                raise ValidationError('This account has been deactivated.')
            
            # Handle admin login
            if user.is_superuser:
                login(request, user)
                request.session['user_role'] = 'admin'
                return redirect('admin_dashboard')
            
            # For regular users, set role to buyer (no sellers allowed)
            role = 'buyer'
            
            # Ensure user is in buyer group
            if not user.groups.filter(name='Buyer').exists():
                group, _ = Group.objects.get_or_create(name='Buyer')
                user.groups.add(group)
            
            # Login successful
            login(request, user)
            request.session['user_role'] = role
            
            # Update last login time
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Redirect to appropriate dashboard
            next_url = request.GET.get('next', '')
            if next_url and is_safe_url(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            
            # All regular users go to fish list
            return redirect('fish_list')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f'Login error: {str(e)}', exc_info=True)
            messages.error(request, 'An error occurred during login. Please try again.')
    
    return render(request, 'login.html', {'show_login': True})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    """Custom admin dashboard with statistics and activity"""
    try:
        # Get basic statistics that always work
        total_users = User.objects.filter(is_staff=False).count()
        
        # Initialize with safe defaults
        total_fish = 0
        total_orders = 0
        total_revenue = 0
        recent_orders = []
        recent_activities = []
        
        # Try to get additional data safely
        try:
            from .models import Fish, Order
            total_fish = Fish.objects.count()
            total_orders = Order.objects.count()
            
            # Get recent orders with user info
            recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]
            
            # Add status colors
            for order in recent_orders:
                if hasattr(order, 'status'):
                    if order.status == 'pending':
                        order.status_color = 'warning'
                    elif order.status == 'processing':
                        order.status_color = 'primary'
                    elif order.status == 'delivered':
                        order.status_color = 'success'
                    else:
                        order.status_color = 'danger'
                else:
                    order.status_color = 'secondary'
            
            # Calculate revenue safely
            try:
                total_revenue = Order.objects.filter(status='delivered').aggregate(total=Sum('total_price'))['total'] or 0
            except:
                total_revenue = 0
            
            # Get recent activities
            recent_users = User.objects.filter(is_staff=False).order_by('-date_joined')[:3]
            for user in recent_users:
                recent_activities.append({
                    'icon': '👤',
                    'title': f'New user {user.username} registered',
                    'time': localtime(user.date_joined).strftime('%H:%M')
                })
            
            # Recent orders activities
            for order in Order.objects.select_related('user').order_by('-created_at')[:2]:
                recent_activities.append({
                    'icon': '📦',
                    'title': f'Order #{order.id} placed by {order.user.username}',
                    'time': localtime(order.created_at).strftime('%H:%M')
                })
            
            # Sort activities
            recent_activities.sort(key=lambda x: x['time'], reverse=True)
            recent_activities = recent_activities[:5]
            
        except Exception as model_error:
            logger.error(f'Model access error: {model_error}')
            # Keep defaults if models fail
        
        context = {
            'total_users': total_users,
            'total_fish': total_fish,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'recent_orders': recent_orders,
            'recent_activities': recent_activities,
        }
        
        return render(request, 'admin_dashboard.html', context)
        
    except Exception as e:
        logger.error(f'Admin dashboard error: {str(e)}', exc_info=True)
        # Show a simple error page instead of redirecting
        return render(request, 'admin_dashboard.html', {
            'total_users': 0,
            'total_fish': 0,
            'total_orders': 0,
            'total_revenue': 0,
            'recent_orders': [],
            'recent_activities': [],
            'error': 'Dashboard temporarily unavailable'
        })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_users(request):
    """Admin users management page"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"admin_users view called for user: {request.user.username}, is_superuser: {request.user.is_superuser}")
    
    try:
        from django.core.paginator import Paginator
        
        search_query = request.GET.get('search', '')
        logger.info(f"Search query: {search_query}")
        
        # Get users with error handling
        try:
            users = User.objects.filter(is_staff=False)
            logger.info(f"Found {users.count()} users")
        except Exception as e:
            logger.error(f'Error fetching users: {str(e)}')
            users = User.objects.none()
        
        # Apply search filter
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query)
            )
            logger.info(f"After search filter: {users.count()} users")
        
        # Pagination
        paginator = Paginator(users, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'users': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
        }
        
        logger.info("Rendering admin_users.html template")
        return render(request, 'admin_users.html', context)
        
    except Exception as e:
        logger.error(f'Admin users error: {str(e)}', exc_info=True)
        # Return a basic page with empty data rather than failing
        return render(request, 'admin_users.html', {
            'users': User.objects.none(), 
            'is_paginated': False,
            'page_obj': None,
            'error_message': f'There was an error loading the users: {str(e)}'
        })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_fish(request):
    """Admin fish products management page"""
    try:
        from django.core.paginator import Paginator
        from .models import Fish, FishCategory
        
        search_query = request.GET.get('search', '')
        category_filter = request.GET.get('category', '')
        
        # Get fish products with error handling
        try:
            fish_products = Fish.objects.select_related('category').all()
        except Exception as e:
            logger.error(f'Error fetching fish products: {str(e)}')
            fish_products = Fish.objects.all()
        
        # Apply search filter
        if search_query:
            fish_products = fish_products.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Apply category filter
        if category_filter:
            fish_products = fish_products.filter(category_id=category_filter)
        
        # Get categories with error handling
        try:
            categories = FishCategory.objects.all()
        except Exception as e:
            logger.error(f'Error fetching categories: {str(e)}')
            categories = []
        
        # Get low stock products with error handling
        try:
            low_stock_products = Fish.objects.filter(stock_kg__gt=0, stock_kg__lte=5).select_related('category')
        except Exception as e:
            logger.error(f'Error fetching low stock products: {str(e)}')
            low_stock_products = []
        
        # Pagination
        paginator = Paginator(fish_products, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'fish_products': page_obj,
            'categories': categories,
            'low_stock_products': low_stock_products,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
        }
        
        return render(request, 'admin_fish.html', context)
        
    except Exception as e:
        logger.error(f'Admin fish error: {str(e)}', exc_info=True)
        # Return a basic page with empty data rather than failing
        return render(request, 'admin_fish.html', {
            'fish_products': [], 
            'categories': [], 
            'low_stock_products': [],
            'error_message': 'There was an error loading the fish products. Please try again.'
        })

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_add(request):
    """API endpoint to add new user"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        is_active = data.get('is_active', True)
        
        # Validate data
        if not username or not email:
            return JsonResponse({'success': False, 'error': 'Username and email are required'})
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Username already exists'})
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already exists'})
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=is_active
        )
        
        return JsonResponse({'success': True, 'message': 'User created successfully'})
        
    except Exception as e:
        logger.error(f'Admin user add error: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_edit(request, user_id):
    """API endpoint to edit user"""
    try:
        user = get_object_or_404(User, id=user_id, is_staff=False)
        data = json.loads(request.body)
        
        # Update fields
        if 'username' in data:
            if User.objects.exclude(id=user_id).filter(username=data['username']).exists():
                return JsonResponse({'success': False, 'error': 'Username already exists'})
            user.username = data['username']
        
        if 'email' in data:
            if User.objects.exclude(id=user_id).filter(email=data['email']).exists():
                return JsonResponse({'success': False, 'error': 'Email already exists'})
            user.email = data['email']
        
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        if 'is_active' in data:
            user.is_active = data['is_active']
        
        user.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'User updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'date_joined': user.date_joined.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f'Admin user edit error: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_toggle_status(request, user_id):
    """API endpoint to toggle user status"""
    try:
        user = get_object_or_404(User, id=user_id, is_staff=False)
        user.is_active = not user.is_active
        user.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully'
        })
        
    except Exception as e:
        logger.error(f'Admin user toggle status error: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_user_delete(request, user_id):
    """API endpoint to delete user"""
    try:
        user = get_object_or_404(User, id=user_id, is_staff=False)
        user.delete()
        
        return JsonResponse({'success': True, 'message': 'User deleted successfully'})
        
    except Exception as e:
        logger.error(f'Admin user delete error: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_fish_add(request):
    """API endpoint to add new fish product"""
    try:
        from .models import Fish, FishCategory
        
        name = request.POST.get('name')
        category_id = request.POST.get('category')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        description = request.POST.get('description', '')
        is_available = request.POST.get('is_available', 'True') == 'True'
        image = request.FILES.get('image')
        
        # Validate data
        if not name or not category_id or not price or not stock:
            return JsonResponse({'success': False, 'error': 'Name, category, price, and stock are required'})
        
        category = get_object_or_404(FishCategory, id=category_id)
        
        # Create fish product with correct field names
        fish = Fish.objects.create(
            name=name,
            category=category,
            price_per_kg=float(price),  # Correct field name
            stock_kg=float(stock),       # Correct field name
            description=description,
            is_available=is_available,
            image=image if image else None
        )
        
        return JsonResponse({'success': True, 'message': 'Fish product created successfully'})
        
    except Exception as e:
        logger.error(f'Admin fish add error: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_fish_edit(request, fish_id):
    """API endpoint to edit fish product"""
    try:
        from .models import Fish, FishCategory
        
        fish = get_object_or_404(Fish, id=fish_id)
        
        # Handle form data
        if request.content_type.startswith('multipart/form-data'):
            name = request.POST.get('name', fish.name)
            category_id = request.POST.get('category', fish.category.id)
            price = request.POST.get('price', fish.price_per_kg)
            stock = request.POST.get('stock', fish.stock_kg)
            description = request.POST.get('description', fish.description)
            is_available = request.POST.get('is_available', str(fish.is_available)) == 'True'
            image = request.FILES.get('image')
            
            # Update fields with correct names
            if name != fish.name:
                fish.name = name
            
            if category_id != str(fish.category.id):
                fish.category = get_object_or_404(FishCategory, id=category_id)
            
            fish.price_per_kg = float(price)  # Correct field name
            fish.stock_kg = float(stock)       # Correct field name
            fish.description = description
            fish.is_available = is_available
            
            if image:
                fish.image = image
            
            fish.save()
            
            return JsonResponse({'success': True, 'message': 'Fish product updated successfully'})
        
        # Handle JSON data for GET requests
        return JsonResponse({
            'success': True,
            'fish': {
                'id': fish.id,
                'name': fish.name,
                'category': fish.category.id,
                'price': str(fish.price_per_kg),  # Correct field name
                'stock': str(fish.stock_kg),      # Correct field name
                'description': fish.description,
                'is_available': fish.is_available
            }
        })
        
    except Exception as e:
        logger.error(f'Admin fish edit error: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_fish_toggle_status(request, fish_id):
    """API endpoint to toggle fish product status"""
    try:
        from .models import Fish
        
        fish = get_object_or_404(Fish, id=fish_id)
        fish.is_available = not fish.is_available
        fish.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Fish product {"shown" if fish.is_available else "hidden"} successfully'
        })
        
    except Exception as e:
        logger.error(f'Admin fish toggle status error: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_fish_delete(request, fish_id):
    """API endpoint to delete fish product"""
    try:
        from .models import Fish
        
        fish = get_object_or_404(Fish, id=fish_id)
        fish.delete()
        
        return JsonResponse({'success': True, 'message': 'Fish product deleted successfully'})
        
    except Exception as e:
        logger.error(f'Admin fish delete error: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})

def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def buyer_dashboard(request):
    """Simple buyer dashboard placeholder — redirect to fish list for now."""
    # Keeping this minimal avoids import errors from urls.py and can be
    # expanded later to a real dashboard view.
    return redirect('fish_list')



@login_required
def fish_list(request):
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    
    # Start with all available fish
    fish_items = Fish.objects.filter(is_available=True)
    
    # Apply search filter
    if search_query:
        fish_items = fish_items.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Apply category filter
    if category_id:
        fish_items = fish_items.filter(category_id=category_id)
    
    # Apply a consistent default ordering without exposing sorting controls
    fish_items = fish_items.order_by('name')
    
    # Pagination
    paginator = Paginator(fish_items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = FishCategory.objects.all()
    
    context = {
        'page_obj': page_obj,
        'fish_items': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        # sorting removed from UI; keep ordering internal only
    }
    return render(request, 'fish_list.html', context)

@login_required
def fish_detail(request, fish_id):
    fish = get_object_or_404(Fish, id=fish_id, is_available=True)
    related_fish = Fish.objects.filter(
        category=fish.category, 
        is_available=True
    ).exclude(id=fish_id)[:4]
    
    # Get feedback for this fish from completed orders
    feedback_list = []
    
    # Get all order items for this fish that have been completed
    completed_order_items = OrderItem.objects.filter(
        fish=fish,
        order__status='completed'
    ).select_related('order')
    
    # Get the order IDs for these items
    order_ids = completed_order_items.values_list('order_id', flat=True).distinct()
    
    # Get feedback for these orders
    feedback_list = OrderFeedback.objects.filter(
        order_id__in=order_ids
    ).select_related('buyer', 'order').order_by('-created_at')
    
    # Calculate average rating and count for this fish
    if feedback_list.exists():
        average_rating = sum(f.rating for f in feedback_list) / len(feedback_list)
        rating_count = len(feedback_list)
    else:
        average_rating = 0
        rating_count = 0
    
    # Check if the current user has purchased this fish
    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        order__status='completed',
        fish=fish
    ).exists()
    
    # Check if user can leave feedback
    can_leave_feedback = has_purchased and not OrderFeedback.objects.filter(
        order__user=request.user,
        order__items__fish=fish,
        order__status='completed'
    ).exists()
    
    context = {
        'fish': fish,
        'related_fish': related_fish,
        'feedback_list': feedback_list,
        'average_rating': average_rating,
        'rating_count': rating_count,
        'can_leave_feedback': can_leave_feedback,
        'has_purchased': has_purchased,
    }
    
    return render(request, 'fish_detail.html', context)


@login_required
def submit_feedback(request, fish_id):
    """Allow a buyer who purchased this fish to submit a rating and comment."""
    fish = get_object_or_404(Fish, id=fish_id, is_available=True)

    if request.method != 'POST':
        return redirect('fish_detail', fish_id=fish.id)

    # Ensure user has at least one completed order for this fish
    completed_items = OrderItem.objects.filter(
        order__user=request.user,
        order__status='completed',
        fish=fish,
    ).select_related('order').order_by('-order__created_at')

    if not completed_items.exists():
        messages.error(request, 'You can only review products you have purchased.')
        return redirect('fish_detail', fish_id=fish.id)

    # Use the most recent completed order for this fish
    order = completed_items.first().order

    # Prevent duplicate feedback for this order
    if hasattr(order, 'feedback'):
        messages.error(request, 'You have already left feedback for this order.')
        return redirect('fish_detail', fish_id=fish.id)

    try:
        rating = int(request.POST.get('rating', '0'))
    except (TypeError, ValueError):
        rating = 0

    comment = (request.POST.get('comment', '') or '').strip()

    if rating not in dict(OrderFeedback.RATING_CHOICES).keys():
        messages.error(request, 'Please select a valid rating.')
        return redirect('fish_detail', fish_id=fish.id)

    OrderFeedback.objects.create(
        order=order,
        buyer=request.user,
        rating=rating,
        comment=comment,
    )

    messages.success(request, 'Thank you for your review!')
    return redirect('fish_detail', fish_id=fish.id)

@login_required
def add_to_cart(request, fish_id):
    if request.method == 'POST':
        try:
            fish = get_object_or_404(Fish, id=fish_id, is_available=True)
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            quantity_kg = Decimal(request.POST.get('quantity', '1'))
            
            if quantity_kg <= 0:
                return JsonResponse({'success': False, 'message': 'Invalid quantity'})
            
            if quantity_kg > fish.stock_kg:
                return JsonResponse({'success': False, 'message': 'Not enough stock available'})
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                fish=fish,
                defaults={'quantity_kg': quantity_kg}
            )
            
            if not created:
                cart_item.quantity_kg += quantity_kg
                if cart_item.quantity_kg > fish.stock_kg:
                    cart_item.quantity_kg = fish.stock_kg
                cart_item.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'{fish.name} added to cart',
                'cart_count': cart.get_total_items()
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'cart.html', context)

@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        try:
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            quantity_kg = Decimal(request.POST.get('quantity', '0'))
            
            if quantity_kg <= 0:
                cart_item.delete()
                return JsonResponse({'success': True, 'message': 'Item removed from cart'})
            
            if quantity_kg > cart_item.fish.stock_kg:
                return JsonResponse({'success': False, 'message': 'Not enough stock available'})
            
            cart_item.quantity_kg = quantity_kg
            cart_item.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Cart updated',
                'item_total': float(cart_item.total_price),
                'cart_total': float(cart_item.cart.get_total_amount())
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def remove_from_cart(request, item_id):
    if request.method == 'POST':
        try:
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            fish_name = cart_item.fish.name
            cart_item.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'{fish_name} removed from cart'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def checkout(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')
    
    if request.method == 'POST':
        try:
            # Create order
            # Prefer address snapshot from POST if provided; otherwise, use profile
            address_snapshot = (request.POST.get('address', '') or '').strip()
            if not address_snapshot:
                try:
                    address_snapshot = request.user.profile.formatted_address()
                except Exception:
                    address_snapshot = ''
            payment_method = request.POST.get('payment_method', 'cod')
            contact_number = (request.POST.get('contact_number', '') or '').strip()

            # Validate contact number (digits only, length 10-15)
            if not re.fullmatch(r"\d{10,15}", contact_number):
                messages.error(request, 'Please enter a valid contact number (digits only, 10–15 characters).')
                context = {
                    'cart': cart,
                    'cart_items': cart_items,
                }
                return render(request, 'checkout.html', context)

            # Include contact number in address snapshot for this order
            if address_snapshot:
                address_snapshot = f"{address_snapshot}\nContact: {contact_number}"
            else:
                address_snapshot = f"Contact: {contact_number}"
            order = Order.objects.create(
                user=request.user,
                total_amount=cart.get_total_amount(),
                notes=request.POST.get('notes', ''),
                payment_method=payment_method,
                delivery_address=address_snapshot
            )
            
            # Create order items
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    fish=cart_item.fish,
                    quantity_kg=cart_item.quantity_kg,
                    unit_price=cart_item.fish.price_per_kg
                )
                
                # Update fish stock and availability
                fish = cart_item.fish
                fish.stock_kg -= cart_item.quantity_kg
                if fish.stock_kg <= 0:
                    fish.stock_kg = Decimal('0.00')
                    fish.is_available = False
                fish.save()
            
            # Clear cart
            cart_items.delete()
            
            # Low stock notification for admin if any item falls below threshold
            LOW_STOCK_THRESHOLD = Decimal('5.00')
            low_stock_fish = [oi.fish.name for oi in order.items.all() if oi.fish.stock_kg <= LOW_STOCK_THRESHOLD]
            if low_stock_fish:
                messages.warning(request, f"Low stock alert: {', '.join(low_stock_fish)}")

            messages.success(request, f'Order #{order.id} placed successfully!')
            return redirect('order_detail', order_id=order.id)
            
        except Exception as e:
            messages.error(request, f'Error placing order: {str(e)}')
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'checkout.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Add success message if this is a newly created order (no messages yet)
    if not request.GET.get('no_message'):
        messages.success(request, f'Order #{order.id} placed successfully! Your order is being processed.')
    
    # Pick a default admin (first staff user) to route buyer messages
    admin_user = User.objects.filter(is_staff=True).order_by('id').first()
    
    context = {
        'order': order,
        'admin_user': admin_user,
    }
    return render(request, 'order_detail_individual.html', context)

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'orders': page_obj,
    }
    return render(request, 'order_history.html', context)


@login_required
@require_POST
def order_now(request):
    """Create an order directly from the 'Order Now' modal for a single fish item."""
    try:
        fish_id = request.POST.get('fish_id')
        quantity = request.POST.get('quantity')
        payment_method = request.POST.get('payment_method', 'cod')
        address_snapshot = (request.POST.get('address', '') or '').strip()
        notes = request.POST.get('notes', '').strip()
        contact_number = (request.POST.get('contact_number', '') or '').strip()

        if not fish_id or not quantity:
            return JsonResponse({'success': False, 'message': 'Missing item or quantity'}, status=400)

        fish = get_object_or_404(Fish, id=fish_id, is_available=True)

        try:
            qty = Decimal(quantity)
            if qty <= 0:
                return JsonResponse({'success': False, 'message': 'Invalid quantity'}, status=400)
        except (DecimalException, ValueError):
            return JsonResponse({'success': False, 'message': 'Invalid quantity value'}, status=400)

        if qty > fish.stock_kg:
            return JsonResponse({'success': False, 'message': 'Not enough stock available'}, status=400)

        # Validate payment method
        valid_methods = dict(Order._meta.get_field('payment_method').choices).keys()
        if payment_method not in valid_methods:
            payment_method = 'cod'

        # Validate contact number (digits only, length 10-15)
        if not re.fullmatch(r"\d{10,15}", contact_number):
            return JsonResponse({'success': False, 'message': 'Please enter a valid contact number (digits only, 10–15 characters).'}, status=400)

        # Fallback to saved address if no snapshot provided
        if not address_snapshot:
            try:
                address_snapshot = request.user.profile.formatted_address()
            except Exception:
                address_snapshot = ''

        # Append contact number to address snapshot for this order
        if address_snapshot:
            address_snapshot = f"{address_snapshot}\nContact: {contact_number}"
        else:
            address_snapshot = f"Contact: {contact_number}"

        # Create order and item
        order = Order.objects.create(
            user=request.user,
            total_amount=qty * fish.price_per_kg,
            notes=notes,
            payment_method=payment_method,
            delivery_address=address_snapshot,
        )

        OrderItem.objects.create(
            order=order,
            fish=fish,
            quantity_kg=qty,
            unit_price=fish.price_per_kg,
        )

        # Update stock
        fish.stock_kg -= qty
        if fish.stock_kg <= 0:
            fish.stock_kg = Decimal('0.00')
            fish.is_available = False
        fish.save()

        return JsonResponse({
            'success': True,
            'message': f'Order #{order.id} placed successfully!',
            'order_id': order.id,
            'redirect_url': f"/orders/{order.id}/",
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def location_select(request):
    if request.method == 'POST':
        # Persist to user profile and also keep in session for quick display
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.country = request.POST.get('country', '')
        profile.province = request.POST.get('province', '')
        profile.municipality = request.POST.get('municipality', '')
        profile.barangay = request.POST.get('barangay', '')
        profile.details = request.POST.get('details', '')
        profile.lat = request.POST.get('lat', '')
        profile.lng = request.POST.get('lng', '')
        profile.save()
        request.session['location'] = {
            'country': profile.country,
            'province': profile.province,
            'municipality': profile.municipality,
            'barangay': profile.barangay,
            'details': profile.details,
            'lat': profile.lat,
            'lng': profile.lng,
        }
        messages.success(request, 'Location saved successfully.')
        return redirect('fish_list')
    # Pre-fill from session if available
    try:
        profile = request.user.profile
        location = {
            'country': profile.country,
            'province': profile.province,
            'municipality': profile.municipality,
            'barangay': profile.barangay,
            'details': profile.details,
            'lat': profile.lat,
            'lng': profile.lng,
        }
    except Exception:
        location = request.session.get('location', {})
    return render(request, 'location_select.html', {'location': location})


# --- Admin Panel Views ---
@login_required
def admin_products(request):
    if not request.user.is_staff:
        return redirect('home')
    search = request.GET.get('search', '')
    qs = Fish.objects.all()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
    categories = FishCategory.objects.all()
    return render(request, 'admin/products.html', {
        'fish_list': qs.order_by('-updated_at')[:200],
        'categories': categories,
    })

@login_required
def admin_orders(request):
    if not request.user.is_staff:
        return redirect('home')
    status = request.GET.get('status', '')
    user_q = request.GET.get('user', '')
    date = request.GET.get('date', '')
    orders = Order.objects.all()
    if status:
        orders = orders.filter(status=status)
    if user_q:
        orders = orders.filter(Q(user__username__icontains=user_q) | Q(user__first_name__icontains=user_q) | Q(user__last_name__icontains=user_q))
    if date:
        orders = orders.filter(created_at__date=date)
    return render(request, 'admin/orders.html', {'orders': orders.order_by('-created_at')[:200]})


@login_required
def admin_orders_data(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    status = request.GET.get('status', '')
    user_q = request.GET.get('user', '')
    date = request.GET.get('date', '')
    orders = Order.objects.all()
    if status:
        orders = orders.filter(status=status)
    if user_q:
        orders = orders.filter(Q(user__username__icontains=user_q) | Q(user__first_name__icontains=user_q) | Q(user__last_name__icontains=user_q))
    if date:
        orders = orders.filter(created_at__date=date)
    data = []
    for o in orders.select_related('user').prefetch_related('items__fish')[:200]:
        data.append({
            'id': o.id,
            'user': o.user.username,
            'items': [{'fish': i.fish.name, 'qty': float(i.quantity_kg)} for i in o.items.all()],
            'total': float(o.total_amount),
            'payment': o.payment_method,
            'address': o.delivery_address,
            'created_at': localtime(o.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            'status': o.status,
        })
    return JsonResponse({'orders': data})


@login_required
def user_orders_data(request):
    # Return current user's orders for live updates in order_history
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    data = []
    for o in orders.prefetch_related('items__fish')[:200]:
        data.append({
            'id': o.id,
            'created_at': localtime(o.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            'status': o.get_status_display(),
            'total': float(o.total_amount),
            'items': [{'fish': i.fish.name, 'qty': float(i.quantity_kg)} for i in o.items.all()],
        })
    # Return the assembled data as JSON
    return JsonResponse({'orders': data})


# --- Messaging System Views ---
@login_required
def message_center(request):
    """Message center for buyers and admin"""
    user_role = request.session.get('user_role')
    
    # Get conversations (messages where user is sender or recipient)
    conversations = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).order_by('-created_at').distinct()
    
    # Get unread count
    unread_count = Message.objects.filter(recipient=request.user, is_read=False).count()
    
    context = {
        'conversations': conversations,
        'unread_count': unread_count,
        'user_role': user_role,
    }
    return render(request, 'message_center.html', context)


@login_required
def send_message(request):
    """Send a new message"""
    if request.method == 'POST':
        recipient_username = request.POST.get('recipient')
        message_type = request.POST.get('message_type', 'general')
        subject = request.POST.get('subject')
        content = request.POST.get('content')
        
        if not recipient_username or not subject or not content:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('message_center')
        
        try:
            recipient = User.objects.get(username=recipient_username)
            
            # Create message
            Message.objects.create(
                sender=request.user,
                recipient=recipient,
                message_type=message_type,
                subject=subject,
                content=content
            )
            
            messages.success(request, f'Message sent to {recipient.username} successfully!')
            return redirect('message_center')
            
        except User.DoesNotExist:
            messages.error(request, 'Recipient not found.')
            return redirect('message_center')
    
    return redirect('message_center')


@login_required
def view_message(request, message_id):
    """View a specific message and mark as read"""
    message = get_object_or_404(Message, id=message_id)
    
    # Check if user is sender or recipient
    if message.sender != request.user and message.recipient != request.user:
        messages.error(request, 'Access denied.')
        return redirect('message_center')
    
    # Get thread messages (replies to this message)
    thread_messages = Message.objects.filter(
        Q(parent_message=message) | Q(id=message.id)
    ).order_by('created_at')
    
    # Mark as read if user is recipient
    if message.recipient == request.user and not message.is_read:
        message.is_read = True
        message.save()
    
    context = {
        'message': message,
        'replies': thread_messages,
    }
    return render(request, 'message_detail.html', context)


@login_required
def reply_message(request, message_id):
    """Reply to a message"""
    original_message = get_object_or_404(Message, id=message_id)
    
    # Check if user is sender or recipient
    if original_message.sender != request.user and original_message.recipient != request.user:
        messages.error(request, 'Access denied.')
        return redirect('message_center')
    
    if request.method == 'POST':
        content = request.POST.get('content')
        
        if not content:
            messages.error(request, 'Please enter a message.')
            return redirect('view_message', message_id=message_id)
        
        # Create reply
        Message.objects.create(
            sender=request.user,
            recipient=original_message.sender if original_message.recipient == request.user else original_message.recipient,
            message_type=original_message.message_type,
            subject=f"Re: {original_message.subject}",
            content=content
        )
        
        messages.success(request, 'Reply sent successfully!')
        return redirect('view_message', message_id=message_id)
    
    context = {
        'original_message': original_message,
    }
    return render(request, 'reply_message.html', context)


@login_required
def order_feedback(request, order_id):
    """Leave feedback for an order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Check if feedback already exists
    if hasattr(order, 'feedback'):
        messages.info(request, 'You have already left feedback for this order.')
        return redirect('order_detail', order_id=order_id)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        if not rating:
            messages.error(request, 'Please select a rating.')
            return redirect('order_feedback', order_id=order_id)
        
        try:
            OrderFeedback.objects.create(
                order=order,
                buyer=request.user,
                rating=int(rating),
                comment=comment
            )
            # Auto-create a message thread to the admin so the buyer can track it
            admin_user = User.objects.filter(is_staff=True).order_by('id').first()
            if admin_user:
                try:
                    Message.objects.create(
                        sender=request.user,
                        recipient=admin_user,
                        message_type='product',
                        subject=f'Feedback for Order #{order.id}',
                        content=f'Rating: {int(rating)}\nComment: {comment or "(no comment)"}'
                    )
                except Exception:
                    pass
            
            messages.success(request, 'Thank you for your feedback!')
            return redirect('order_detail', order_id=order_id)
            
        except (ValueError, TypeError):
            messages.error(request, 'Invalid rating selected.')
            return redirect('order_feedback', order_id=order_id)
    
    context = {
        'order': order,
    }
    return render(request, 'order_feedback.html', context)
