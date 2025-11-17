from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch

from payments.models import PaymentMethod, Customer

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
        self.user = User.objects.create_user(username='testuser',email= 'test@user.com', password='testpassword123')
        self.client.force_authenticate(user=self.user)

        self.list_create_url = reverse('payment-method-list-create')

        # Objeto de prueba que simularemos que Stripe nos devuelve
        self.mock_stripe_pm = MockStripePaymentMethod(
            id="pm_tok_123456real",
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
    @patch('payments.views.stripe.Customer.modify')
    @patch('payments.views.stripe.PaymentMethod.attach')
    @patch('payments.views.stripe.PaymentMethod.retrieve')
    @patch('payments.views.stripe.Customer.create')
    def test_add_payment_method(self,
                                mock_stripe_customer_create,  # 1.
                                mock_stripe_pm_retrieve,  # 2.
                                mock_stripe_pm_attach,  # 3.
                                mock_stripe_customer_modify):  # 4.
        """
        Prueba POST /api/v1/payment-methods/
        """
        # 1. Configurar los "engaños" (mocks)

        # Cuando se llame a stripe.Customer.create(), devuelve un customer_id falso
        # Usamos .id en lugar de un diccionario para simular el objeto de Stripe
        mock_stripe_customer_create.return_value = type('MockStripeCustomer', (object,), {'id': 'cus_12345fake'})()

        # Cuando se llame a stripe.PaymentMethod.retrieve(), devuelve nuestro objeto falso
        mock_stripe_pm_retrieve.return_value = self.mock_stripe_pm

        # Los otros dos (attach, modify) no necesitan devolver nada
        mock_stripe_pm_attach.return_value = None
        mock_stripe_customer_modify.return_value = None

        # 2. Datos de la petición
        data = {
            "token": "pm_tok_123456fake",  # El token que nos daría el frontend
            "make_default": True
        }

        # 3. Llamar a la API
        response = self.client.post(self.list_create_url, data, format='json')

        # 4. Verificar que la API respondió 201 (Creado)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 5. Verificar que se guardó en la BBDD
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(PaymentMethod.objects.count(), 1)
        pm = PaymentMethod.objects.get()

        # 6. Verificar que los datos del mock se guardaron
        self.assertEqual(pm.user, self.user)
        self.assertEqual(pm.psp_ref, "pm_tok_123456real")  # de self.mock_stripe_pm
        self.assertEqual(pm.brand, "visa")
        self.assertEqual(pm.last4, "4242")
        self.assertTrue(pm.is_default)

        # 7. Verificar que las APIs de Stripe fueron llamadas
        mock_stripe_customer_create.assert_called_once()
        mock_stripe_pm_retrieve.assert_called_once_with("pm_tok_123456fake")
        mock_stripe_pm_attach.assert_called_once_with("pm_tok_123456fake", customer="cus_12345fake")
        mock_stripe_customer_modify.assert_called_once()

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