from django.urls import path
from .views import (
    CartRetrieveAPIView,
    CartItemAddAPIView,
    CartItemDestroyAPIView
)

urlpatterns = [
    # GET /api/v1/cart/ (Ver mi carrito con totales)
    path('cart/',
         CartRetrieveAPIView.as_view(),
         name='cart-retrieve'),

    # POST /api/v1/cart/items/ (Añadir item al carrito)
    path('cart/items/',
         CartItemAddAPIView.as_view(),
         name='cart-item-add'),

    # DELETE /api/v1/cart/items/<pk>/ (Eliminar item del carrito)
    path('cart/items/<int:pk>/',
         CartItemDestroyAPIView.as_view(),
         name='cart-item-destroy'),
]