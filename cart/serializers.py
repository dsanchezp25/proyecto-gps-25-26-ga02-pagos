from rest_framework import serializers
from .models import ShoppingCart, CartItem
from pricing.services import calculate_cart_totals

# Serializer para añadir un ítem al carrito
class CartItemAddSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['product_id', 'quantity']

# Serializer para mostrar el carrito completo
class CartItemDisplaySerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity', 'price_at_addition']

# Serializer para MOSTRAR el carrito de compras completo
class ShoppingCartSerializer(serializers.ModelSerializer):
    items = CartItemDisplaySerializer(many=True, read_only=True)

    # Campos calculados por el servicio pricing
    subtotal = serializers.SerializerMethodField()
    tax_rate_name = serializers.SerializerMethodField()
    tax_rate_percent = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingCart
        fields = [
            'id', 'user', 'status', 'items',
            'subtotal', 'tax_rate_name', 'tax_rate_percent',
            'tax_amount', 'total'
        ]

    def get_totals(self, obj):
        """
        Llama al servicio de pricing para obtener los totales del carrito.
        """
        if not hasattr(self, '_totals'): # Cachear el resultado para no llamar varias veces
            region_code = self.context.get('region_code', None)
            self._totals = calculate_cart_totals(obj, region_code)
        return self._totals

    def get_subtotal(self, obj):
        return self.get_totals(obj)['subtotal']

    def get_tax_rate_name(self, obj):
        return self.get_totals(obj)['tax_rate_name']

    def get_tax_rate_percent(self, obj):
        return self.get_totals(obj)['tax_rate_percent']

    def get_tax_amount(self, obj):
        return self.get_totals(obj)['tax_amount']

    def get_total(self, obj):
        return self.get_totals(obj)['total']