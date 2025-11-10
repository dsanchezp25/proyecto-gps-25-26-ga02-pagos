from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from decimal import Decimal

from cart.models import ShoppingCart, CartItem
from pricing.models import TaxRate, RegionTaxRule
from .models import Order, OrderItem

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
            product_id=101,
            quantity=2,
            price_at_addition="100.00"
        )

        # URL de creación: intenta sin namespace, luego con namespace, y por último literal.
        try:
            self.create_order_url = reverse("order-list-create")
        except Exception:
            try:
                self.create_order_url = reverse("orders:order-list-create")
            except Exception:
                self.create_order_url = "/api/v1/orders/"

    def test_create_order_from_cart(self):
        payload = {"region_code": "ES"}
        response = self.client.post(self.create_order_url, data=payload, format='json')

        # Si falla, muestra el contenido de respuesta para ver el error real
        if response.status_code not in (status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED):
            detail = getattr(response, "data", None)
            if detail is None:
                detail = getattr(response, "content", b"")
            self.fail(f"POST /orders devolvió {response.status_code}. Respuesta: {detail!r}")

        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()

        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, ShoppingCart.CartStatus.ORDERED)

        self.assertEqual(order.status, Order.OrderStatus.PENDING)
        self.assertEqual(order.subtotal, Decimal("200.00"))
        self.assertEqual(order.tax_total, Decimal("20.00"))
        self.assertEqual(order.amount, Decimal("220.00"))

    def test_get_order_details(self):
        payload = {"region_code": "ES"}
        create_resp = self.client.post(self.create_order_url, data=payload, format='json')
        if create_resp.status_code not in (status.HTTP_201_CREATED, status.HTTP_202_ACCEPTED):
            detail = getattr(create_resp, "data", None)
            if detail is None:
                detail = getattr(create_resp, "content", b"")
            self.fail(f"POST /orders devolvió {create_resp.status_code}. Respuesta: {detail!r}")

        order = Order.objects.get()

        # URL de detalle: intenta sin namespace, luego con namespace, y por último literal.
        try:
            retrieve_url = reverse("order-retrieve", kwargs={"order_id": str(order.order_id)})
        except Exception:
            try:
                retrieve_url = reverse("orders:order-retrieve", kwargs={"order_id": str(order.order_id)})
            except Exception:
                retrieve_url = f"/api/v1/orders/{order.order_id}/"

        response = self.client.get(retrieve_url)

        detail = getattr(response, "data", None)
        if detail is None:
            detail = getattr(response, "content", b"")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Respuesta detalle: {detail!r}")
        self.assertEqual(response.data['order_id'], str(order.order_id))
        self.assertEqual(response.data['amount'], "220.00")
