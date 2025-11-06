from rest_framework import serializers
from .models import ShoppingCart, CartItem
from pricing.services import calculate_cart_totals

class CartItemSerializer(serializers.ModelSerializer):
    """
        Serializer para Añadir/Listar/Actualizar/Eliminar ítems del carrito
    """
    class Meta:
        model = CartItem
        # El campo 'cart' se asginará automáticamente en la vista
        # basandonos en el carrito del usuario autenticado
        fields = ['id', 'product_id', 'quantity', 'price_at_addition']
        read_only_fields = ['id']

    def validate_product_id(self, value):
        if value <= 0:
            raise serializers.ValidationError("El product_id debe ser un entero positivo.")
        return value


class ShoppingCartSerializer (serializers.ModelSerializer):
    """
        Serializer para ver el carrito completo con sus ítems
    """
    # Usamos el 'related_name' (items) que definimos en el modelo
    items = CartItemSerializer(many=True, read_only=True)

    subtotal = serializers.SerializerMethodField()
    tax_rate_name = serializers.SerializerMethodField()
    tax_rate_percent = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingCart
        fields = ['id', 'user', 'created_at', 'updated_at', 'items',
                  'subtotal', 'tax_rate_name', 'tax_rate_percent', 'total']
        read_only_fields = fields

    def get_totals(self, obj):
        # 'context' es un 'state bag' que podemos usar en el serializer.
        if not hasattr(self, '_totals'):
            #Sacamos la region_code del context que pasamos desde la vista
            region_code = self.context.get('region_code', None)

            # Llamamos al servicio para calcular los totales
            self._totals = calculate_cart_totals(obj, region_code)  # obj es el ShoppingCart
        return self._totals

    # --- METODOS PARA CADA CAMPO DE TOTALIZACIÓN ---
    def get_subtotal(self, obj):
        return self.get_totals(obj)["subtotal"]

    def get_tax_rate_name(self, obj):
        return self.get_totals(obj)["tax_rate_name"]

    def get_tax_rate_percent(self, obj):
        return self.get_totals(obj)["tax_rate_percent"]

    def get_tax_amount(self, obj):
        return self.get_totals(obj)["tax_amount"]

    def get_total(self, obj):
        return self.get_totals(obj)["total"]
