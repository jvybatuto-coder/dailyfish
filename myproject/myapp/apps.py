from django.apps import AppConfig


class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'

    def ready(self):
        """Import signals when Django app is ready"""
        # Import signals (no database operations here)
        import myapp.signals
