from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from .models import ShoppingCart, CartItem

User = get_user_model()

class CartBehaviorTests(APITestCase):

    def setUp(self):
        """ Configura el entorno para CADA prueba """
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword123',
        )

        # setUp crea el carrito con el estado 'ACTIVE' por defecto
        self.cart = ShoppingCart.objects.get(user=self.user)

        self.list_create_url = reverse('cart-item-list')
        self.summary_url = reverse('cart-item-get-cart-summary')

    def test_cart_is_created_active(self):
        """
        Verifica que el carrito se crea con estado 'ACTIVE' por defecto
        """
        response = self.client.get(self.summary_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificamos el estado que añadimos en el modelo
        self.assertEqual(response.data['status'], 'ACTIVE')

    def test_list_empty_cart_behavior(self):
        """
        Verifica que listar un carrito vacío devuelve una lista vacía
        """
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_add_item_behavior(self):
        data = {"product_id": 101, "quantity": 2, "price_at_addition": "19.99"}
        response = self.client.post(self.list_create_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.objects.get().product_id, 101)

    def test_delete_item_behavior(self):
        item = CartItem.objects.create(
            cart=self.cart,
            product_id=101,
            quantity=1,
            price_at_addition="19.99"
        )
        delete_url = reverse('cart-item-detail', kwargs={'pk': item.pk})
        response = self.client.delete(delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_add_existing_item_behavior(self):
        """
        Verifica que agregar un ítem existente actualiza la cantidad
        """
        CartItem.objects.create(
            cart=self.cart,
            product_id=101,
            quantity=1,
            price_at_addition="19.99"
        )
        data = {"product_id": 101, "quantity": 2, "price_at_addition": "19.99"}
        response = self.client.post(self.list_create_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.objects.get().quantity,3)

    def test_unauthenticated_behavior(self):
        """
        Verifica que las operaciones sin autenticación son rechazadas
        """
        self.client.force_authenticate(user=None)
        response_get = self.client.get(self.list_create_url)
        self.assertEqual(response_get.status_code, status.HTTP_401_UNAUTHORIZED)