from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Order, OrderItem
from cart.models import ShoppingCart  # Necesitamos el carrito para crearlo
from pricing.services import calculate_cart_totals  # Necesitamos el servicio de impuestos

from .serializers import (
    CreateOrderRequestSerializer,
    OrderAcceptedResponseSerializer,
    OrderResponseSerializer
)

# Corresponde a: POST /api/v1/orders
class OrderListCreateAPIView(APIView):
    """
    Corresponde a: POST /api/v1/orders
    Crea una nueva orden a partir de los datos del carrito.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Crea una orden (carrito -> orden).
        Ignoramos el CreateOrderRequest del .yml por ahora y usamos
        nuestro propio flujo (basado en el carrito) para crear la orden.
        """

        # TODO: En un futuro, deberíamos validar con CreateOrderRequestSerializer
        # serializer = CreateOrderRequestSerializer(data=request.data)
        # if not serializer.is_valid():
        #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Obtener el carrito activo del usuario
            cart = get_object_or_404(
                ShoppingCart,
                user=request.user,
                status=ShoppingCart.CartStatus.ACTIVE
            )
            cart_items = cart.items.all()

            if not cart_items:
                return Response({"error": "El carrito está vacío."}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Obtener la región (simplificado)
            # TODO: obtener region_code del perfil del usuario o del request
            region_code = "ES"

            # 3. Calcular totales
            totals = calculate_cart_totals(cart, region_code)

            # 4. Crear la Orden y los Items (en una transacción)
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user,
                    status=Order.OrderStatus.PENDING,  # La orden está PENDIENTE hasta que se pague
                    amount=totals['total'],
                    currency="EUR",  # TODO: Sacar de 'totals' o 'request'
                    subtotal=totals['subtotal'],
                    tax_total=totals['tax_amount'],
                    tax_percent=totals['tax_rate_percent'],
                    tax_name=totals['tax_rate_name']
                )

                # 5. Copiar los artículos del carrito al pedido
                order_items_to_create = []
                for item in cart_items:
                    order_items_to_create.append(
                        OrderItem(
                            order=order,
                            item_type=OrderItem.ItemType.TRACK,  # TODO: Detectar tipo real
                            product_id=item.product_id,
                            quantity=item.quantity,
                            unit_price=item.price_at_addition
                        )
                    )
                OrderItem.objects.bulk_create(order_items_to_create)

                # 6. Vaciar el carrito (marcarlo como procesado)
                cart.status = ShoppingCart.CartStatus.ORDERED
                cart.save()
                # Opcional: cart.items.all().delete()

            # 7. Devolver la respuesta 'OrderAcceptedResponse'
            response_serializer = OrderAcceptedResponseSerializer(order)
            # El .yml dice 202 (Accepted), lo cual es correcto
            return Response(response_serializer.data, status=status.HTTP_202_ACCEPTED)

        except ShoppingCart.DoesNotExist:
            return Response({"error": "No se encontró un carrito activo."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Error interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Corresponde a: GET /api/v1/orders/{order_id}
class OrderRetrieveAPIView(generics.RetrieveAPIView):
    """
    Corresponde a: GET /api/v1/orders/{order_id}
    Obtiene el detalle de una orden específica.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OrderResponseSerializer
    queryset = Order.objects.all()

    # 'lookup_field' le dice a DRF que use 'order_id' (el UUID)
    # en lugar de 'pk' (el ID numérico) para buscar en la URL.
    lookup_field = 'order_id'

    def get_queryset(self):
        """Asegura que un usuario solo pueda ver sus propias órdenes."""
        return Order.objects.filter(user=self.request.user)