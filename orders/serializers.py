from rest_framework import serializers
from .models import Order, OrderItem

# --- 1. Serializers de ENTRADA (Validación del Request) ---

# Serializer para los artículos dentro de un pedido
class OrderItemInputSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=OrderItem.ItemType.choices)
    item_id = serializers.CharField(max_length=100)
    qty = serializers.IntegerField(min_value=1)

    def validate_item_id(self, value):
        # Validamos que el ID (str) sea en realidad un numero
        try:
            return int(value)
        except ValueError:
            raise serializers.ValidationError("El ID del artículo debe ser un número válido.")

# Serializer para la creación de un pedido
class CreateOrderRequestSerializer(serializers.Serializer):
    currency = serializers.CharField(max_length=3)
    items = OrderItemInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("La lista de artículos no puede estar vacía.")
        return value


# --- 2. Serializers de SALIDA (Respuesta de la API) ---

# Serializer para los artículos dentro de un pedido (respuesta)
class OrderLineResponseSerializer(serializers.ModelSerializer):
    order_line_id = serializers.IntegerField(source='pk')
    item_id = serializers.CharField(source='product_id')
    qty = serializers.IntegerField(source='quantity')

    class Meta:
        model = OrderItem
        fields = [
            'order_line_id',
            'item_type',
            'item_id',
            'qty',
            'unit_price',
        ]

# Serializer para la respuesta del pedido
class OrderResponseSerializer(serializers.ModelSerializer):
    lines = OrderLineResponseSerializer(many=True, read_only=True)
    user_id = serializers.IntegerField(source='user.id')

    class Meta:
        model = Order
        fields = [
            'order_id',
            'user_id',
            'amount',
            'currency',
            'status',
            'created_at',
            'lines'
        ]

# Serializer para la respuesta de aceptación del pedido
class OrderAcceptedResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['order_id', 'status']