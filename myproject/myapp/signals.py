from django.db.models.signals import post_migrate
from django.contrib.auth.models import User
from django.dispatch import receiver

@receiver(post_migrate)
def create_superuser(sender, **kwargs):
    if sender.name == 'auth':
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@dailyfish.com',
                password='admin123'
            )
            print("Superuser 'admin' created automatically!")
        else:
            print("Superuser 'admin' already exists!")
