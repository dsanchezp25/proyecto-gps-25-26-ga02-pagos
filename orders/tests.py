from itertools import product

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.urls import reverse

from cart.models import ShoppingCart, CartItem
from pricing.models import TaxRate, RegionTaxRule
from .models import Order

User = get_user_model()

class OrderAPITest(APITestCase):

    def setUp(self):
        # 1. Crear un usuario de prueba
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)

        # 2. Crear reglas de impuestos
        tax = TaxRate.objects.create(name="IVA Test", rate=10.00)
        RegionTaxRule.objects.create(region_code="ES", tax_rate=tax)

        # 3. Crear carrito con items
        self.cart = ShoppingCart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=self.cart,
            product_is=101,
            quantity=2,
            price_at_addition="100.00"
        )

        # 4. URL para crear pedido desde carrito
        self.create_order_url = reverse('order-create-from-cart')

    def test_create_order_from_cart(self):
        """
        Prueba la creación del pedido y la validez fiscal.
        """
        data = {"region_code": "ES"}
        response = self.client.post(self.create_order_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 1. Verificar que se creó 1 pedido
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()

        # 2. Verificar que el carrito se marcó como "ORDERED"
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, ShoppingCart.CartStatus.ORDERED)

        # 3. Verificar validez fiscal de los datos (Subtotal=200, Tax=10%, Total=220)
        self.assertEqual(order.subtotal, 200.00)
        self.assertEqual(order.tax_percent, 10.00)
        self.assertEqual(order.tax_total, 20.00)
        self.assertEqual(order.total_paid, 220.00)

        # 4. Verificar que el PDF se generó y almacenó
        self.assertIsNotNone(order.invoice_pdf)
        self.assertTrue(order.invoice_pdf.name.startswith('invoices/'))

    def test_download_invoice(self):
        """
        Prueba la descarga (recuperación) del PDF.
        """
        # 1. Crear un pedido primero
        data = {"region_code": "ES"}
        self.client.post(self.create_order_url, data, format='json')
        order = Order.objects.get()

        # 2. Obtener la URL de descarga
        download_url = reverse('order-download-invoice', kwargs={'pk': order.pk})
        response = self.client.get(download_url)

        # 3. Verificar que la respuesta es un fichero PDF
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].includes(order.invoice_pdf.name))

    def test_create_order_empty_cart(self):
        """
        Prueba de validación (carrito vacío).
        """
        # Vaciar el carrito
        self.cart.items.all().delete()

        data = {"region_code": "ES"}
        response = self.client.post(self.create_order_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "El carrito está vacío.")