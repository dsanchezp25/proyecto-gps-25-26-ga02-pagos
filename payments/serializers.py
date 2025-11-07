from rest_framework import serializers
from .models import PaymentMethod

# Añadir un nuevo métdo de pago
class AddPaymentMethodRequestSerializer(serializers.Serializer):
    provider = serializers.CharField(max_length=50, default="stripe")
    # 'token' es el ID del PaymentMethod que nos da Stripe (ej. "pm_...")
    token = serializers.CharField(max_length=255)
    make_default = serializers.BooleanField(default=True)

# Serializador para los métodos de pago
class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            'payment_method_id',
            'provider',
            'psp_ref',
            'brand',
            'last4',
            'exp_mm',
            'exp_yy',
            'is_default'
        ]