from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_new import (
    UserViewSet, CategoryViewSet, ProductViewSet, OrderViewSet,
    CartViewSet, MessageViewSet, FeedbackViewSet, dashboard_stats
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'carts', CartViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'feedback', FeedbackViewSet)

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/stats/', dashboard_stats, name='dashboard_stats'),
]
