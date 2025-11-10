from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch  # <-- Importante para "engañar" a Stripe

from .models import PaymentMethod

User = get_user_model()


# 1. Este es el objeto falso que "engañará" a Stripe
class MockStripePaymentMethod:
    """
    Un objeto falso que simula la respuesta de stripe.PaymentMethod.retrieve()
    """

    def __init__(self, id, brand, last4, exp_month, exp_year):
        self.id = id
        self.card = self.MockStripeCard(brand, last4, exp_month, exp_year)

    class MockStripeCard:
        def __init__(self, brand, last4, exp_month, exp_year):
            self.brand = brand
            self.last4 = last4
            self.exp_month = exp_month
            self.exp_year = exp_year


# --- Pruebas de la API ---
class PaymentMethodAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123')
        self.client.force_authenticate(user=self.user)

        self.list_create_url = reverse('payment-method-list-create')

        # Objeto de prueba que simularemos que Stripe nos devuelve
        self.mock_stripe_pm = MockStripePaymentMethod(
            id="pm_tok_123456real",  # psp_ref
            brand="visa",
            last4="4242",
            exp_month=12,
            exp_year=2030
        )

    def test_list_empty_payment_methods(self):
        """
        Prueba GET /api/v1/payment-methods/ (cuando está vacío)
        """
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    # Usamos @patch para interceptar la llamada a Stripe
    @patch('stripe.PaymentMethod.retrieve')
    def test_add_payment_method(self, mock_stripe_retrieve):
        """
        Prueba POST /api/v1/payment-methods/
        """
        # Configuramos el "engaño":
        # Cuando se llame a stripe.PaymentMethod.retrieve(), devuelve nuestro objeto falso
        mock_stripe_retrieve.return_value = self.mock_stripe_pm

        data = {
            "token": "pm_tok_123456fake",  # El token que nos daría el frontend
            "make_default": True
        }
        response = self.client.post(self.list_create_url, data, format='json')

        # 1. Verificar que la API respondió 201 (Creado)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 2. Verificar que se guardó en la BBDD
        self.assertEqual(PaymentMethod.objects.count(), 1)
        pm = PaymentMethod.objects.get()

        # 3. Verificar que los datos de Stripe se guardaron correctamente
        self.assertEqual(pm.user, self.user)
        self.assertEqual(pm.psp_ref, "pm_tok_123456real")
        self.assertEqual(pm.brand, "visa")
        self.assertEqual(pm.last4, "4242")
        self.assertEqual(pm.exp_yy, 2030)
        self.assertTrue(pm.is_default)

        # 4. Verificar que la API de Stripe fue llamada con el token correcto
        mock_stripe_retrieve.assert_called_once_with("pm_tok_123456fake")

    def test_delete_payment_method(self):
        """
        Prueba DELETE /api/v1/payment-methods/<pm_id>/
        """
        # 1. Creamos un método de pago para borrar
        pm = PaymentMethod.objects.create(
            user=self.user,
            payment_method_id="pm_test_abc",  # Nuestro ID interno
            psp_ref="pm_tok_real_xyz",
            brand="mastercard",
            last4="1234"
        )

        # 2. Obtenemos la URL de borrado
        delete_url = reverse('payment-method-destroy', kwargs={'payment_method_id': pm.payment_method_id})

        # 3. Hacemos la llamada DELETE
        response = self.client.delete(delete_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PaymentMethod.objects.count(), 0)

    def test_user_cannot_delete_other_users_pm(self):
        """
        Prueba de seguridad: Un usuario no puede borrar tarjetas de otro
        """
        # 1. Creamos un segundo usuario
        other_user = User.objects.create_user(username='otheruser', password='password')

        # 2. Creamos un PM para ESE usuario
        pm = PaymentMethod.objects.create(
            user=other_user,  # <- Pertenece a other_user
            payment_method_id="pm_test_other",
            psp_ref="pm_tok_real_xyz",
        )

        # 3. Intentamos borrarlo estando logueados como 'self.user'
        delete_url = reverse('payment-method-destroy', kwargs={'payment_method_id': pm.payment_method_id})
        response = self.client.delete(delete_url)

        # 4. Debería dar 404 (No Encontrado) porque el queryset no lo encuentra
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(PaymentMethod.objects.count(), 1)  # Sigue existiendo