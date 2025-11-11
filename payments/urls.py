from django.urls import path
from .views import (
    PaymentMethodListCreateAPIView,
    PaymentMethodDestroyAPIView,
    PaymentIntentCreateAPIView,
    StripeWebhookAPIView
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

    # POST /api/v1/payments/intent/
    path('payments/intent/',
         PaymentIntentCreateAPIView.as_view(),
         name='payment-intent-create'),

    # POST /api/v1/webhooks/stripe/
    # Webhook para recibir eventos de Stripe
    path('webhooks/stripe/',
         StripeWebhookAPIView.as_view(),
         name='webhook-stripe'),
]