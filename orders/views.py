from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import FileResponse

from .models import Order
from .serializers import OrderSerializer
from .services import create_order_from_cart


class OrderViewSet(
    mixins.ListModelMixin,  # GET /api/v1/orders/ (Listar mis pedidos)
    mixins.RetrieveModelMixin,  # GET /api/v1/orders/<pk>/ (Ver un pedido)
    viewsets.GenericViewSet
):
    """
    API para gestionar Pedidos y Facturas.
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Solo mostrar al usuario sus propios pedidos
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='create-from-cart')
    def create_from_cart(self, request):
        """
        POST /api/v1/orders/create-from-cart/
        Endpoint para "Comprar". Convierte el carrito en un pedido.
        """
        try:
            # Obtener la región (igual que en el carrito)
            region_code = request.data.get('region_code', None)

            order = create_order_from_cart(request.user, region_code)

            serializer = self.get_serializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Error interno: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='download-invoice')
    def download_invoice(self, request, pk=None):
        """
        GET /api/v1/orders/<pk>/download-invoice/
        Permite la "recuperación" (descarga) del PDF.
        """
        order = self.get_object()  # Obtiene el pedido (y valida que es del usuario)

        if not order.invoice_pdf:
            return Response({"error": "Factura no generada o no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # Devuelve el fichero para descargar
        return FileResponse(order.invoice_pdf.open(), as_attachment=True, filename=order.invoice_pdf.name)