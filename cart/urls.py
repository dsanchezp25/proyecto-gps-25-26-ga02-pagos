from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartItemViewSet

# El Router de DRF crea automáticamente las URLs para
# Listar, Añadir, Actualizar y Eliminar.
router = DefaultRouter()
router.register(r'cart-items', CartItemViewSet, basename='cart-item')

urlpatterns = [
    path('', include(router.urls)),
]