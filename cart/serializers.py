from rest_framework import serializers
from .models import ShoppingCart, CartItem

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

    # Añadimos un campo 'total' calculado
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingCart
        fields = ['id', 'user', 'created_at', 'updated_at', 'items', 'total_price']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'items', 'total_price']

    def get_total_price(self, obj):
        # Calcula el total: precio * cantidad para cada ítem
        total = sum(item.price_at_addition * item.quantity for item in obj.items.all())
