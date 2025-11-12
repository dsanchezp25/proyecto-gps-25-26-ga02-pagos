from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from decimal import Decimal

from cart.models import ShoppingCart, CartItem
from pricing.models import TaxRate, RegionTaxRule
from orders.models import Order, OrderItem

User = get_user_model()

class OrderRefactorTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        self.client.force_authenticate(user=self.user)

        # Impuestos usando Decimal
        tax = TaxRate.objects.create(name="IVA Test", rate=Decimal("10.00"))
        RegionTaxRule.objects.create(region_code="ES", tax_rate=tax)

        self.cart = ShoppingCart.objects.create(user=self.user, status=ShoppingCart.CartStatus.ACTIVE)

        CartItem.objects.create(
            cart=self.cart,
            product_id=101, # <--- La versión corregida
            quantity=2,
            price_at_addition="100.00"
        )

        # Usamos la URL nueva
        self.create_order_url = reverse("orders:order-list-create")

    def test_create_order_from_cart(self):
        payload = {"region_code": "ES"}
        response = self.client.post(self.create_order_url, data=payload, format='json')

        # Comprobamos la respuesta de la API nueva
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()

        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, ShoppingCart.CartStatus.ORDERED)

        # Comprobamos los campos nuevos
        self.assertEqual(order.status, Order.OrderStatus.PENDING)
        self.assertEqual(order.subtotal, Decimal("200.00"))
        self.assertEqual(order.tax_total, Decimal("20.00"))
        self.assertEqual(order.amount, Decimal("220.00")) # <- Campo 'amount'

    def test_get_order_details(self):
        payload = {"region_code": "ES"}
        self.client.post(self.create_order_url, data=payload, format='json')
        order = Order.objects.get()

        # Usamos la URL nueva
        retrieve_url = reverse('orders:order-retrieve', kwargs={'order_id': order.order_id})
        response = self.client.get(retrieve_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['order_id'], str(order.order_id))
        self.assertEqual(response.data['amount'], "220.00") # <- Campo 'amount'