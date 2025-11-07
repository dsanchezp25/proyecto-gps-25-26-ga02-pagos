from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderListCreateAPIView, OrderRetrieveAPIView


# POST /api/v1/orders
# GET /api/v1/orders/{order_id}

urlpatterns = [
    path('orders/',
         OrderListCreateAPIView.as_view(),
         name='order-list-create'),

    path('orders/<uuid:order_id>/',
         OrderRetrieveAPIView.as_view(),
         name='order-retrieve'),

    # TODO: Aún nos falta el endpoint para descargar el PDF.
    # Lo añadiremos después de implementar el pago real (Stripe).
]