from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.ReadOnlyField()
    class Meta:
        model = OrderItem
        fields = ['product_id', 'quantity', 'price', 'line_total']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    invoice_pdf_url = serializers.FileField(source='invoice_pdf', read_only=True)

    class Meta:
        model = Order
        fields = [
            'order_id', 'status', 'created_at', 'items',
            'subtotal', 'tax_total', 'tax_percent', 'tax_name', 'total_paid',
            'invoice_pdf_url'
        ]