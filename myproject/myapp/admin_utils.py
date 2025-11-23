from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def create_admin_user(request):
    """Temporary endpoint to create admin user"""
    if request.method == 'POST':
        username = 'pelaez'
        password = 'pelaez123'
        
        try:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(username=username, password=password)
                return JsonResponse({'status': 'success', 'message': f'Admin user "{username}" created successfully!'})
            else:
                user = User.objects.get(username=username)
                user.is_staff = True
                user.is_superuser = True
                user.set_password(password)
                user.save()
                return JsonResponse({'status': 'success', 'message': f'Admin user "{username}" updated successfully!'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'info', 'message': 'Use POST request to create admin user'})
