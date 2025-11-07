from django.urls import path
from .views import (
    PaymentMethodListCreateAPIView,
    PaymentMethodDestroyAPIView
)

urlpatterns = [
    # GET, POST /api/v1/payment-methods/
    path('payment-methods/',
         PaymentMethodListCreateAPIView.as_view(),
         name='payment-method-list-create'),

    # DELETE /api/v1/payment-methods/<pm_id>/
    path('payment-methods/<str:payment_method_id>/',
         PaymentMethodDestroyAPIView.as_view(),
         name='payment-method-destroy'),
]