from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from .models import ShoppingCart, CartItem
from .serializers import ShoppingCartSerializer, CartItemSerializer

class CartItemViewSet(
    mixins.CreateModelMixin, # POST (add item to cart)
    mixins.UpdateModelMixin, # PUT/PATCH (update item quantity)
    mixins.DestroyModelMixin, # DELETE (remove item from cart)
    mixins.ListModelMixin, # GET (list items in cart)
    viewsets.GenericViewSet
):
    """
    API para gestionar los Items del Carrito del usuario autenticado
    - LISTAR (GET /api/v1/cart-items/): Lista los items de tu carrito.
    - AÑADIR (POST /api/v1/cart-items/): Añade un item a tu carrito.
    - ACTUALIZAR (PUT /api/v1/cart-items/<id>/): Actualiza la cantidad.
    - ELIMINAR (DELETE /api/v1/cart-items/<id>/): Elimina un item.
    """
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated] # Solo usuarios autenticados

    def get_queryset(self):
        """
        Sobreescribimos esto para CADA usuario vea SOLO sus items del carrito.
        """
        # Obtenemos el carrito del usuario autenticado
        cart, created = ShoppingCart.objects.get_or_create(user=self.request.user)
        # Devolvemos solo los items de ese carrito
        return CartItem.objects.filter(cart=cart)

    def perform_create(self, serializer):
        """
        Sobreescribimos para asignar el carrito del usuario
        automaticamente al añadir un item
        """
        cart, created = ShoppingCart.objects.get_or_create(user=self.request.user)

        # Antes de guardar, vemos si el producto ya existe en el carrito
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity', 1]

        try:
            # Si ya existe, actualizamos la cantidad
            existing_item = CartItem.objects.get(cart=cart, product_id=product_id)
            existing_item.quantity += quantity
            existing_item.price_at_addition = serializer.validated_data.get('price_at_addition')
            existing_item.save()
            # Acutalizamos el 'instance' para que no se cree un nuevo item
            serializer.instance = existing_item
        except CartItem.DoesNotExist:
            # Si no existe, creamos uno nuevo
            serializer.save(cart=cart)

@action(detail=True, methods=['get'], url_path='summary')
def get_cart_summary(self, request):
    """
    Endpoint extra para ver el carrito COMPLETO (summary)
    GET /api/v1/cart-items/summary/

    Se puede pasar la región como query param opcional 'region'
    Ejemplo: /api/v1/cart-items/summary/?region=ES-CN

    """
    cart, created = ShoppingCart.objects.get_or_create(user=self.request.user)

    # 1. Obtener la región desde la url
    region_code = request.query_params.get('region', None)

    # 2. Preparar el 'context' para el serializer
    serializer_context = {
        'request': request,
        'region_code': region_code
    }

    # 3. Serializar el carrito completo
    serializer = ShoppingCartSerializer(cart, context=serializer_context)

    return Response(serializer.data, status=status.HTTP_200_OK)

