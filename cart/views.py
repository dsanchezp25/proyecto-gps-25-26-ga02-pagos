from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import ShoppingCart, CartItem
from .serializers import (
    ShoppingCartSerializer,
    CartItemAddSerializer,
    CartItemDisplaySerializer
)

def get_or_create_cart(user):
    """ Función helper para obtener/crear el carrito activo """
    try:
        # 1. Intenta obtener el carrito activo
        cart = ShoppingCart.objects.get(user=user, status=ShoppingCart.CartStatus.ACTIVE)
    except ShoppingCart.DoesNotExist:
        # 2. Si no existe, busca si hay uno 'ORDERED'
        ShoppingCart.objects.filter(
            user=user,
            status=ShoppingCart.CartStatus.ORDERED
        ).delete()

        # 3. (Ya sea que no existía o que borramos el 'ORDERED'), creamos uno nuevo
        cart = ShoppingCart.objects.create(user=user, status=ShoppingCart.CartStatus.ACTIVE)

    return cart

class CartRetrieveAPIView(generics.RetrieveAPIView):
    """
    Corresponde a: GET /api/v1/cart/
    Obtiene el carrito completo del usuario, con totales e impuestos.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ShoppingCartSerializer

    def get_object(self):
        # Devuelve el carrito activo del usuario que hace la petición
        return get_or_create_cart(self.request.user)

    def get_serializer_context(self):
        # Pasamos la 'region_code' del query param (ej. ?region=ES-CN)
        # al serializer para que el servicio de pricing la use.
        context = super().get_serializer_context()
        context['region_code'] = self.request.query_params.get('region', None)
        return context


class CartItemAddAPIView(generics.CreateAPIView):
    """
    Corresponde a: POST /api/v1/cart/items/
    Añade un item al carrito (o actualiza su cantidad si ya existe).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CartItemAddSerializer

    # Sobrescribimos la funcion para manejar la lógica de añadir/actualizar
    def perform_create(self, serializer):
        cart = get_or_create_cart(self.request.user)

        product_id = serializer.validated_data.get('product_id')
        quantity = serializer.validated_data.get('quantity', 1)

        try:
            # Si ya existe, actualizamos la cantidad
            item = CartItem.objects.get(cart=cart, product_id=product_id)
            item.quantity += quantity
            item.price_at_addition = serializer.validated_data.get('price_at_addition')
            item.save()
            serializer.instance = item  # Devolvemos el item actualizado
        except CartItem.DoesNotExist:
            # Si no existe, lo creamos
            serializer.save(cart=cart)

    # Sobrescribimos para que la RESPUESTA use el serializer de Display
    def get_serializer(self, *args, **kwargs):
        # Sobrescribimos para que la RESPUESTA use el serializer de Display
        if 'instance' in kwargs:
            kwargs['context'] = self.get_serializer_context()
            return CartItemDisplaySerializer(*args, **kwargs)
        return super().get_serializer(*args, **kwargs)


class CartItemDestroyAPIView(generics.DestroyAPIView):
    """
    Corresponde a: DELETE /api/v1/cart/items/{item_id}/
    Elimina un item específico del carrito.
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'  # Usará el ID del CartItem

    def get_queryset(self):
        # Solo permite borrar items del carrito del propio usuario
        cart = get_or_create_cart(self.request.user)
        return CartItem.objects.filter(cart=cart)