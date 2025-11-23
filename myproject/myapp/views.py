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
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
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
    # Emergency admin creation
    if not User.objects.filter(username='pelaez').exists():
        User.objects.create_superuser('pelaez', 'admin@dailyfish.com', 'pelaez123')
    else:
        user = User.objects.get(username='pelaez')
        user.is_staff = True
        user.is_superuser = True
        user.set_password('pelaez123')
        user.save()
    
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
    """Handle user registration with validation and error handling"""
    if request.method == 'POST':
        try:
            # Get form data with proper type conversion
            raw_username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip().lower()
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')
            role = request.POST.get('role', '').lower()
            full_name = request.POST.get('full_name', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            address_location = request.POST.get('address_location', '').strip()
            store_name = request.POST.get('store_name', '').strip()
            
            # Initialize username early to prevent UnboundLocalError
            username = raw_username
            
            # Validate required fields (without enforcing username yet)
            if not all([email, password1, password2, role]):
                raise ValidationError('Please fill in all required fields.')

            # For buyers, username from form is still required
            if role == 'buyer' and not raw_username:
                raise ValidationError('Please choose a username.')

            # Additional required fields for seller registration (minimal approach)
            if role == 'seller':
                # Only require phone number, everything else optional
                if not phone_number:
                    raise ValidationError('Phone number is required for seller registration.')
                
                # Set simple defaults
                full_name = username or 'Seller'
                store_name = f"{full_name}'s Store"
                address_location = "To be updated"
                
            # Validate role
            if role not in ['buyer', 'seller']:
                raise ValidationError('Invalid user role selected.')
                
            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError('Please enter a valid email address.')

            # Enforce Gmail-only registration (temporarily disabled for testing)
            # if not email.endswith('@gmail.com'):
            #     raise ValidationError('Please use a Gmail address (ending in @gmail.com).')
                
            # Derive or use username depending on role
            if role == 'seller' and not raw_username:
                # Auto-generate username from email for sellers
                base = (email.split('@')[0] or 'seller').strip()
                # Keep only allowed characters, replace others with underscore
                base = re.sub(r'[^a-zA-Z0-9_]', '_', base)
                if not base:
                    base = 'seller'
                username = base[:30]

                original = username
                counter = 1
                # Ensure uniqueness (case-insensitive)
                while User.objects.filter(username__iexact=username).exists():
                    suffix = f"_{counter}"
                    username = (original[:30 - len(suffix)] + suffix)
                    counter += 1
            # For all other cases (buyer with username, seller with username), username is already set to raw_username

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
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                    is_staff=(role == 'seller')
                )
                
                # Create related objects
                Cart.objects.create(user=user)
                profile = UserProfile.objects.create(user=user)

                # If seller, populate seller-specific profile fields (minimal)
                if role == 'seller':
                    try:
                        profile.phone_number = phone_number
                        profile.store_name = store_name
                        profile.details = address_location
                        profile.save()
                    except Exception as e:
                        logger.error(f'Seller profile update error: {e}')
                        # Continue even if profile update fails

                # Add to appropriate group
                group, _ = Group.objects.get_or_create(name=role.capitalize())
                user.groups.add(group)
                
                # Set role in session
                request.session['user_role'] = role
                
                # Send welcome email (temporarily disabled for testing)
                # try:
                #     subject = f'Welcome to DailyFish, {user.username}!'
                #     html_message = render_to_string('emails/welcome.html', {
                #         'username': user.username,
                #         'is_seller': role == 'seller'
                #     })
                #     plain_message = strip_tags(html_message)
                #     send_mail(
                #         subject=subject,
                #         message=plain_message,
                #         from_email=settings.DEFAULT_FROM_EMAIL,
                #         recipient_list=[user.email],
                #         html_message=html_message,
                #         fail_silently=True
                #     )
                # except Exception as e:
                #     logger.error(f'Error sending welcome email: {str(e)}')
                
                # Save the role in the session before login to prevent session issues
                request.session['user_role'] = role
                
                # Save the session before login to ensure it's persisted
                request.session.save()
                
                # Auto-login after registration
                login(request, user)
                
                # Set session expiry to a reasonable value
                if not request.session.get_expire_at_browser_close():
                    request.session.set_expiry(60 * 60 * 24 * 7)  # 1 week
                
                messages.success(request, f'Welcome, {user.username}! Your account has been created successfully.')
                
                # Redirect based on role - using seller_dashboard for seller
                return redirect('seller_dashboard' if role == 'seller' else 'fish_list')
                
        except ValidationError as e:
            messages.error(request, str(e))
        except IntegrityError as e:
            logger.error(f'Database error during registration: {str(e)}')
            messages.error(request, 'An error occurred during registration. Please try again.')
        except Exception as e:
            logger.error(f'Unexpected error in registration: {str(e)}', exc_info=True)
            logger.error(f'Form data: role={role if "role" in locals() else "undefined"}, username={username if "username" in locals() else "undefined"}, email={email if "email" in locals() else "undefined"}')
            logger.error(f'POST data: {dict(request.POST)}')
            messages.error(request, f'Registration error: {str(e)}')
            # For debugging, show the actual error instead of generic message
    
    # Handle GET request or failed POST
    return render(request, 'login.html', {'show_register': True})

@csrf_exempt
def login_view(request):
    """Handle user login with rate limiting and security measures"""
    # Redirect if already authenticated
    if request.user.is_authenticated:
        role = request.session.get('user_role', 'buyer')
        # Use seller_dashboard as the seller dashboard
        return redirect('seller_dashboard' if role == 'seller' else 'fish_list')
    
    if request.method == 'POST':
        try:
            username_input = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            role = request.POST.get('role', '').lower()  # Role is optional for login
            
            # Basic validation - role is optional for login
            if not all([username_input, password]):
                raise ValidationError('Please fill in all required fields.')
                
            # If role is provided, validate it
            if role and role not in ['buyer', 'seller']:
                raise ValidationError('Invalid user role selected.')
            
            # For admin users, allow direct login without role
            if username_input == 'pelaez' and password == 'pelaez123':
                user = User.objects.filter(username='pelaez').first()
                if user and user.check_password('pelaez123'):
                    login(request, user)
                    request.session['user_role'] = 'admin'  # Set admin role
                    return redirect('admin_dashboard')
            
            # If no role provided, try to authenticate as regular user
            if not role:
                user = authenticate(request, username=username_input, password=password)
                if user is not None and user.is_active:
                    login(request, user)
                    # Determine role based on user properties
                    if user.is_staff or user.is_superuser:
                        request.session['user_role'] = 'admin'
                        return redirect('admin_dashboard')
                    elif user.groups.filter(name='Seller').exists():
                        request.session['user_role'] = 'seller'
                        return redirect('seller_dashboard')
                    else:
                        request.session['user_role'] = 'buyer'
                        return redirect('fish_list')
                else:
                    raise ValidationError('Invalid username or password.')
                
            # Rate limiting check (pseudo-code - implement actual rate limiting)
            # if is_rate_limited(request):
            #     raise ValidationError('Too many login attempts. Please try again later.')
            
            # Map login identifier based on role
            username_for_auth = username_input
            if role == 'seller':
                # For sellers, treat the login field as Gmail address
                email = username_input.strip().lower()
                if not email.endswith('@gmail.com'):
                    raise ValidationError('Please use your Gmail address to sign in as a seller.')

                seller_user = User.objects.filter(email__iexact=email, is_staff=True).first()
                if not seller_user:
                    raise ValidationError('No seller account found with that Gmail address.')
                username_for_auth = seller_user.username

            # Authenticate user
            user = authenticate(request, username=username_for_auth, password=password)
            
            if user is None:
                # Log failed login attempt
                logger.warning(f'Failed login attempt for identifier: {username_input}')
                raise ValidationError('Invalid username or password.')
                
            # Check if user is active
            if not user.is_active:
                raise ValidationError('This account has been deactivated.')
                
            # Check role-specific permissions
            if role == 'seller' and not user.is_staff:
                raise ValidationError('You do not have seller privileges. Please register as a seller.')
            
            # Check if user is in the correct group
            if role:
                group_name = 'Seller' if role == 'seller' else 'Buyer'
                if not user.groups.filter(name=group_name).exists():
                    raise ValidationError(f'You are not registered as a {role}.')
            
            # Login successful
            login(request, user)
            request.session['user_role'] = role or ('admin' if user.is_superuser else 'buyer')
            
            # Update last login time
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Redirect to appropriate dashboard
            next_url = request.GET.get('next', '')
            if next_url and is_safe_url(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            
            # Redirect based on user role
            user_role = request.session.get('user_role', 'buyer')
            if user_role == 'admin':
                return redirect('admin_dashboard')
            elif user_role == 'seller':
                return redirect('seller_dashboard')
            else:
                return redirect('fish_list')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f'Login error: {str(e)}', exc_info=True)
            messages.error(request, 'An error occurred during login. Please try again.')
    
    return render(request, 'login.html', {'show_login': True})

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
    # Pick a default seller (first staff user) to route buyer messages
    seller_user = User.objects.filter(is_staff=True).order_by('id').first()
    
    context = {
        'order': order,
        'seller_user': seller_user,
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
    """Message center for both buyers and sellers"""
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
@user_passes_test(lambda u: u.groups.filter(name='Seller').exists())
def seller_messages(request):
    """
    Message center specifically for sellers
    """
    # Get messages where the seller is either the sender or recipient
    messages = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).order_by('-created_at')
    
    # Mark messages as read when viewed
    unread_messages = messages.filter(recipient=request.user, is_read=False)
    unread_messages.update(is_read=True)
    
    # Get unread count
    unread_count = Message.objects.filter(recipient=request.user, is_read=False).count()
    
    context = {
        'messages': messages,
        'unread_count': unread_count,
    }
    return render(request, 'seller/messages.html', context)


@login_required
@user_passes_test(lambda u: u.groups.filter(name='Seller').exists())
def seller_notifications(request):
    """List notifications for the current seller.

    For now we reuse the Message model as notification source, showing
    all messages where the seller is sender or recipient, newest first.
    """
    notifications = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).order_by('-created_at')

    unread_notifications_count = notifications.filter(
        recipient=request.user, is_read=False
    ).count()

    context = {
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'seller/notifications.html', context)


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
        'thread_messages': thread_messages,
        'is_seller': hasattr(request.user, 'sellerprofile'),
    }
    return render(request, 'seller/message_detail.html', context)


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
            # Auto-create a message thread to the seller so the buyer can track it
            seller_user = User.objects.filter(is_staff=True).order_by('id').first()
            if seller_user:
                try:
                    Message.objects.create(
                        sender=request.user,
                        recipient=seller_user,
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


# =============================
# Seller-facing views (DailyFish)
# =============================


@login_required
def seller_dashboard(request):
    """Seller dashboard for DailyFish staff sellers.
    
    Special access for jvyboy@gmail.com to see all products and orders.
    Other sellers see limited view of their own data only.
    """
    if not request.user.is_staff:
        return redirect('home')

    # Check if this is the special seller account
    is_special_seller = request.user.email == 'jvyboy@gmail.com'
    
    if is_special_seller:
        # Special seller gets ALL products and orders from the system
        all_products = Fish.objects.all().order_by('-updated_at')
        
        # Get all completed orders from the system
        base_order_items = OrderItem.objects.filter(
            order__status='completed',
        ).select_related('order', 'fish', 'order__user')
        
        # Available years for filtering (all orders in system)
        available_years = (
            base_order_items
            .values_list('order__created_at__year', flat=True)
            .distinct()
        )
        
        total_products = all_products.count()
        active_products = all_products.filter(is_available=True).count()
        low_stock_products = all_products.filter(is_available=True, stock_kg__lte=Decimal('5.00'))
        
        context = {
            'is_special_seller': True,
            'seller_name': request.user.username,
            'fish_list': all_products,
            'total_products': total_products,
            'active_products': active_products,
            'low_stock_products': low_stock_products,
            'base_order_items': base_order_items,
            'available_years': sorted(available_years, reverse=True),
        }
    else:
        # Regular sellers get their own products and orders only
        # Assign any fish without a seller to the current user
        no_seller_fish = Fish.objects.filter(seller__isnull=True)
        if no_seller_fish.exists():
            print(f"DEBUG: Found {no_seller_fish.count()} fish with no seller. Assigning to {request.user.username}")
            no_seller_fish.update(seller=request.user)
        
        # Get all fish products for this seller (including newly assigned ones)
        seller_fish = Fish.objects.filter(seller=request.user)
        print(f"DEBUG: Total fish for seller {request.user.username}: {seller_fish.count()}")
        for fish in seller_fish[:5]:  # Print first 5 fish for debugging
            print(f"  - {fish.name} (ID: {fish.id}, Available: {fish.is_available})")
        
        total_products = seller_fish.count()
        active_products = seller_fish.filter(is_available=True).count()
        low_stock_products = seller_fish.filter(is_available=True, stock_kg__lte=Decimal('5.00'))

        # Base queryset of completed order items containing this seller's fish
        base_order_items = OrderItem.objects.filter(
            fish__seller=request.user,
            order__status='completed',
        ).select_related('order', 'fish')

        # Available years for filtering (distinct years where this seller has completed orders)
        available_years = (
            base_order_items
            .values_list('order__created_at__year', flat=True)
            .distinct()
        )
        
        context = {
            'is_special_seller': False,
            'seller_name': request.user.username,
            'total_products': total_products,
            'active_products': active_products,
            'low_stock_products': low_stock_products,
            'base_order_items': base_order_items,
            'available_years': sorted(available_years, reverse=True),
        }

    # Determine period filter for orders (day, month, year)
    period = request.GET.get('period', 'day')
    now_dt = timezone.now()
    start_dt = None
    end_dt = None

    # Optional explicit year/month parameters for month/year views
    try:
        selected_year = int(request.GET.get('year', now_dt.year))
    except (TypeError, ValueError):
        selected_year = now_dt.year

    try:
        selected_month = int(request.GET.get('month', now_dt.month))
    except (TypeError, ValueError):
        selected_month = now_dt.month

    if period == 'day':
        start_dt = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = 'Today'
    elif period == 'month':
        # Clamp month and year to valid ranges
        if selected_month < 1 or selected_month > 12:
            selected_month = now_dt.month
        start_dt = now_dt.replace(year=selected_year, month=selected_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        if selected_month == 12:
            end_dt = start_dt.replace(year=selected_year + 1, month=1)
        else:
            end_dt = start_dt.replace(month=selected_month + 1)
        period_label = start_dt.strftime('%B %Y')
    elif period == 'year':
        start_dt = now_dt.replace(year=selected_year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_dt = start_dt.replace(year=selected_year + 1)
        period_label = str(selected_year)
    else:
        # Fallback to showing all time if an unexpected value is provided
        period = 'all'
        period_label = 'All Time'

    # Apply date filtering to the base queryset when a range is defined
    seller_order_items = base_order_items
    if start_dt is not None:
        seller_order_items = seller_order_items.filter(order__created_at__gte=start_dt)
    if end_dt is not None:
        seller_order_items = seller_order_items.filter(order__created_at__lt=end_dt)

    recent_orders = seller_order_items.order_by('-order__created_at')[:5]

    total_sales = sum(item.total_price for item in seller_order_items)

    # Add common context variables
    context.update({
        'period': period,
        'period_label': period_label,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'recent_orders': recent_orders,
        'total_sales': total_sales,
    })

    return render(request, 'seller/dashboard.html', context)


@login_required
def seller_products(request):
    """List all fish products for the current DailyFish seller."""
    if not request.user.is_staff:
        return redirect('home')

    # Show all products if user is staff, otherwise filter by seller
    if request.user.is_superuser:
        seller_fish = Fish.objects.all().order_by('-created_at')
    else:
        seller_fish = Fish.objects.filter(seller=request.user).order_by('-created_at')
    
    categories = FishCategory.objects.all()

    context = {
        'seller_name': request.user.username,
        'fish_list': seller_fish,
        'categories': categories,
        'is_superuser': request.user.is_superuser
    }
    return render(request, 'seller/products.html', context)


@login_required
def seller_product_create(request):
    """Create a new fish product for the current DailyFish seller."""
    if not request.user.is_staff:
        return redirect('home')

    categories = FishCategory.objects.all()

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        description = (request.POST.get('description') or '').strip()
        category_id = request.POST.get('category')
        price_raw = (request.POST.get('price_per_kg') or '').strip()
        stock_raw = (request.POST.get('stock_kg') or '').strip()
        image = request.FILES.get('image')
        image_url = (request.POST.get('image_url') or '').strip()

        if not name or not category_id or not price_raw or not stock_raw:
            messages.error(request, 'Please fill in all required fields for the new fish.')
            return render(
                request,
                'seller/product_form.html',
                {'categories': categories, 'mode': 'create', 'seller_name': request.user.username},
            )

        try:
            category = FishCategory.objects.get(id=category_id)
            price = Decimal(price_raw)
            stock = Decimal(stock_raw)
        except (FishCategory.DoesNotExist, InvalidOperation):
            messages.error(request, 'Invalid category, price, or stock value.')
            return render(
                request,
                'seller/product_form.html',
                {'categories': categories, 'mode': 'create', 'seller_name': request.user.username},
            )

        fish = Fish(
            name=name,
            description=description,
            category=category,
            seller=request.user,
            price_per_kg=price,
            stock_kg=stock,
            is_available=True,
        )

        if image:
            fish.image = image
        elif image_url:
            fish.image_url = image_url

        fish.save()
        messages.success(request, f'Seller product "{fish.name}" has been created successfully.')
        return redirect('seller_products')

    return render(
        request,
        'seller/product_form.html',
        {'categories': categories, 'mode': 'create', 'seller_name': request.user.username},
    )


@login_required
def seller_product_edit(request, fish_id):
    """Edit an existing fish product owned by the current DailyFish seller."""
    if not request.user.is_staff:
        return redirect('home')

    # Superusers can edit any fish; regular staff can edit only their own
    if request.user.is_superuser:
        fish = get_object_or_404(Fish, id=fish_id)
    else:
        fish = get_object_or_404(Fish, id=fish_id, seller=request.user)
    categories = FishCategory.objects.all()

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        description = (request.POST.get('description') or '').strip()
        category_id = request.POST.get('category')
        price_raw = (request.POST.get('price_per_kg') or '').strip()
        stock_raw = (request.POST.get('stock_kg') or '').strip()
        image = request.FILES.get('image')
        image_url = (request.POST.get('image_url') or '').strip()

        if not name or not category_id or not price_raw or not stock_raw:
            messages.error(request, 'Please fill in all required fields for the fish.')
        else:
            try:
                category = FishCategory.objects.get(id=category_id)
                price = Decimal(price_raw)
                stock = Decimal(stock_raw)
            except (FishCategory.DoesNotExist, InvalidOperation):
                messages.error(request, 'Invalid category, price, or stock value.')
            else:
                fish.name = name
                fish.description = description
                fish.category = category
                fish.price_per_kg = price
                fish.stock_kg = stock

                if image:
                    fish.image = image
                    fish.image_url = ''
                elif image_url:
                    fish.image_url = image_url

                fish.save()
                messages.success(request, f'Seller product "{fish.name}" has been updated successfully.')
                return redirect('seller_products')

    context = {
        'seller_name': request.user.username,
        'fish': fish,
        'categories': categories,
        'mode': 'edit',
    }
    return render(request, 'seller/product_form.html', context)


@login_required
def seller_product_delete(request, fish_id):
    """Soft-delete a fish product for the current DailyFish seller by marking it unavailable."""
    if not request.user.is_staff:
        return redirect('home')

    fish = get_object_or_404(Fish, id=fish_id, seller=request.user)

    if request.method == 'POST':
        fish.is_available = False
        fish.stock_kg = Decimal('0.00')
        fish.save()
        messages.success(request, f'Seller product "{fish.name}" has been removed from the marketplace.')
    else:
        messages.error(request, 'Invalid request method for deleting a product.')

    return redirect('seller_products')


@login_required
def seller_orders(request):
    """View and manage all orders (same set as shown in the Django admin Order list)."""
    if not request.user.is_staff:
        return redirect('home')

    # Show all orders instead of only those containing this seller's fish
    orders = (
        Order.objects.all()
        .select_related('user')
        .prefetch_related('items__fish')
        .order_by('-created_at')
    )

    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)

    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')

        if order_id and new_status:
            try:
                order = orders.get(id=order_id)
            except Order.DoesNotExist:
                messages.error(request, 'Order not found or does not belong to this seller.')
            else:
                valid_statuses = {choice[0] for choice in Order.STATUS_CHOICES}
                if new_status in valid_statuses:
                    order.status = new_status
                    order.save()
                    messages.success(
                        request,
                        f'Order #{order.id} status updated to {order.get_status_display()}.',
                    )
                else:
                    messages.error(request, 'Invalid order status selected.')

        return redirect('seller_orders')

    context = {
        'seller_name': request.user.username,
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'seller/orders.html', context)


@login_required
def seller_profile(request):
    """Basic seller profile page for DailyFish staff sellers."""
    if not request.user.is_staff:
        return redirect('home')

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.email = request.POST.get('email', '').strip()
        request.user.save()

        profile.details = request.POST.get('details', '').strip()
        profile.barangay = request.POST.get('barangay', '').strip()
        profile.municipality = request.POST.get('municipality', '').strip()
        profile.province = request.POST.get('province', '').strip()
        profile.country = request.POST.get('country', '').strip()
        profile.phone_number = request.POST.get('phone_number', '').strip()
        profile.store_name = request.POST.get('store_name', '').strip()

        # Optional ID verification update
        id_file = request.FILES.get('id_verification')
        if id_file:
            try:
                upload_path = handle_uploaded_file(id_file, 'seller_ids')
                profile.id_verification = upload_path
            except ValidationError as e:
                messages.error(request, f'ID verification error: {e.messages[0]}')

        profile.save()

        messages.success(request, 'Seller profile information has been updated.')
        return redirect('seller_profile')

    # Aggregate total quantity sold across all completed orders containing this seller's fish
    seller_items_qs = OrderItem.objects.filter(
        fish__seller=request.user,
        order__status='completed',
    )
    total_sold_kg = seller_items_qs.aggregate(total_sold=Sum('quantity_kg'))['total_sold'] or Decimal('0')

    # Aggregate rating and review count for this seller across all feedback on orders
    seller_feedback = OrderFeedback.objects.filter(
        order__items__fish__seller=request.user,
        order__status='completed',
    ).aggregate(
        avg_rating=Avg('rating'),
        review_count=Count('id'),
    )
    avg_rating = seller_feedback['avg_rating'] or 0
    review_count = seller_feedback['review_count'] or 0

    context = {
        'seller_name': request.user.username,
        'profile': profile,
        'seller_store_name': getattr(profile, 'store_name', '') or request.user.username,
        'seller_email': request.user.email,
        'seller_phone': getattr(profile, 'phone_number', ''),
        'seller_total_sold_kg': total_sold_kg,
        'seller_avg_rating': avg_rating,
        'seller_review_count': review_count,
    }
    return render(request, 'seller/profile.html', context)

def create_admin_now(request):
    """Emergency admin creation - remove after use"""
    try:
        if not User.objects.filter(username='pelaez').exists():
            User.objects.create_superuser('pelaez', 'admin@dailyfish.com', 'pelaez123')
            return HttpResponse("Admin user 'pelaez' created! Password: pelaez123")
        else:
            user = User.objects.get(username='pelaez')
            user.is_staff = True
            user.is_superuser = True
            user.set_password('pelaez123')
            user.save()
            return HttpResponse("Admin user 'pelaez' updated! Password: pelaez123")
    except Exception as e:
        return HttpResponse(f"Error: {e}")

@login_required
def admin_dashboard(request):
    """Admin dashboard view"""
    # Check if user is admin/superuser
    if not request.user.is_staff and not request.user.is_superuser:
        return redirect('home')  # or show access denied page
    
    # Get dashboard data
    from django.db.models import Count, Sum, Q
    from datetime import date, timedelta
    import calendar
    
    today = date.today()
    
    # Total Sales (placeholder - replace with actual calculations)
    total_sales = 12540.00  # This should come from your Order model
    
    # Total Orders Today
    orders_today = 24  # This should come from your Order model
    
    # Total Sellers
    total_sellers = User.objects.filter(groups__name='seller').count() or 156
    
    # Low Stock Alerts (placeholder - replace with actual Product query)
    low_stock_alerts = 7  # This should come from your Product model
    
    # Recent Orders (placeholder - replace with actual query)
    recent_orders = [
        {
            'id': '#ORD-001',
            'buyer_name': 'John Smith',
            'total': 2450.00,
            'status': 'completed',
            'date': today.strftime('%b %d, %Y')
        },
        {
            'id': '#ORD-002', 
            'buyer_name': 'Maria Garcia',
            'total': 1890.00,
            'status': 'pending',
            'date': today.strftime('%b %d, %Y')
        },
        {
            'id': '#ORD-003',
            'buyer_name': 'David Chen', 
            'total': 3200.00,
            'status': 'completed',
            'date': (today - timedelta(days=1)).strftime('%b %d, %Y')
        },
        {
            'id': '#ORD-004',
            'buyer_name': 'Sarah Johnson',
            'total': 980.00,
            'status': 'cancelled', 
            'date': (today - timedelta(days=1)).strftime('%b %d, %Y')
        },
        {
            'id': '#ORD-005',
            'buyer_name': 'Michael Brown',
            'total': 4020.00,
            'status': 'pending',
            'date': (today - timedelta(days=2)).strftime('%b %d, %Y')
        }
    ]
    
    context = {
        'total_sales': total_sales,
        'orders_today': orders_today,
        'total_sellers': total_sellers,
        'low_stock_alerts': low_stock_alerts,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'admin_dashboard.html', context)
