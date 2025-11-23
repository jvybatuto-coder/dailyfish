from django.apps import AppConfig


class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'

    def ready(self):
        """Import signals when Django app is ready"""
        # Create admin immediately when app loads
        from django.contrib.auth.models import User
        from django.contrib.auth import authenticate
        from django.db import connection
        
        # Only run if tables exist
        if 'auth_user' in connection.introspection.table_names():
            try:
                username = 'admin'
                password = 'admin'
                email = 'admin@dailyfish.com'
                
                # Create or update admin user
                if User.objects.filter(username=username).exists():
                    user = User.objects.get(username=username)
                    user.set_password(password)
                    user.is_superuser = True
                    user.is_staff = True
                    user.is_active = True
                    user.save()
                else:
                    User.objects.create_superuser(
                        username=username,
                        email=email,
                        password=password
                    )
                
                # Test authentication
                auth_user = authenticate(username=username, password=password)
                if auth_user:
                    print(f"Admin user '{username}' ready for login!")
            except Exception as e:
                print(f"Admin creation error: {e}")
        
        # Import signals
        import myapp.signals
