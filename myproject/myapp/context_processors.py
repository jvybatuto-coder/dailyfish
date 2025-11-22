from .models import Cart


def location(request):
    loc = request.session.get('location') or {}
    parts = []
    # Prefer Municipality, Barangay, Province for a concise line
    if loc.get('municipality'):
        parts.append(loc.get('municipality'))
    if loc.get('barangay'):
        parts.append(loc.get('barangay'))
    if loc.get('province'):
        parts.append(loc.get('province'))
    display = ', '.join(parts) if parts else ''
    return {
        'location_display': display
    }


def cart_info(request):
    """Provide cart item count globally so navbar badges can use it."""
    count = 0
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        try:
            cart, _ = Cart.objects.get_or_create(user=user)
            count = cart.get_total_items()
        except Exception:
            count = 0
    return {
        'cart_item_count': count,
    }

