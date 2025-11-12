from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from decimal import Decimal
from cart.views import get_or_create_cart  # <-- Importamos la función helper

from cart.models import ShoppingCart, CartItem
from pricing.models import TaxRate, RegionTaxRule

User = get_user_model()


class CartRefactorTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        self.client.force_authenticate(user=self.user)

        tax = TaxRate.objects.create(name="IVA Test", rate=21.00)
        RegionTaxRule.objects.create(region_code="ES", tax_rate=tax)

        # Apuntamos a las nuevas URLs del refactor
        self.cart_url = reverse('cart-retrieve')
        self.add_item_url = reverse('cart-item-add')

    def test_get_empty_cart(self):
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['items']), 0)
        self.assertEqual(response.data['total'], Decimal("0.00"))  # Comparamos Decimal

    def test_add_item_to_cart(self):
        data = {
            "product_id": 101,
            "quantity": 2,
            "price_at_addition": "10.00"
        }
        response = self.client.post(self.add_item_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # ARREGLO 1: La respuesta es el item, no el carrito
        self.assertEqual(response.data['product_id'], 101)

        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.objects.get().quantity, 2)

    def test_delete_item_from_cart(self):
        cart = get_or_create_cart(self.user)  # Usamos la helper
        item = CartItem.objects.create(
            cart=cart,
            product_id=101,
            quantity=1,
            price_at_addition="9.99"
        )
        delete_url = reverse('cart-item-destroy', kwargs={'pk': item.pk})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.count(), 0)

    def test_get_cart_with_totals(self):
        cart = get_or_create_cart(self.user)  # Usamos la helper
        CartItem.objects.create(cart=cart, product_id=101, quantity=2, price_at_addition="100.00")

        response = self.client.get(self.cart_url + "?region=ES")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # ARREGLO 2: Comparamos Decimales
        self.assertEqual(response.data['subtotal'], Decimal("200.00"))
        self.assertEqual(response.data['tax_amount'], Decimal("42.00"))
        self.assertEqual(response.data['total'], Decimal("242.00"))