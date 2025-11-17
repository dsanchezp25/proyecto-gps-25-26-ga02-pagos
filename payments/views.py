from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
import stripe
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from .models import PaymentMethod, Customer
from .serializers import (
    AddPaymentMethodRequestSerializer,
    PaymentMethodSerializer,
    PaymentIntentRequestSerializer,
    PaymentIntentResponseSerializer,
)
from orders.models import Order
# ¡¡IMPORTANTE!! Asegúrate de que tu 'services.py' SÍ tiene estas funciones
from .services import handle_payment_intent_failed, handle_payment_intent_succeeded

# Configurar Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


def get_or_create_stripe_customer(user):
    """
    Busca o crea un Customer en nuestra BBDD y en Stripe.
    Versión robusta que comprueba si el cliente existe en Stripe.
    """
    try:
        # 1. Busca en nuestra BBDD
        customer = Customer.objects.get(user=user)

        # 2. Verificamos si el cliente AÚN EXISTE en Stripe
        try:
            stripe.Customer.retrieve(customer.stripe_customer_id)
            return customer.stripe_customer_id

        except stripe.InvalidRequestError:
            # 3. ¡El cliente NO existe en Stripe! (Error 'No such customer')
            logger.warning(f"Borrando Customer local 'stale' {customer.stripe_customer_id} para user {user.id}")
            customer.delete()
            raise Customer.DoesNotExist  # Forzamos que vaya al bloque 'except'

    except Customer.DoesNotExist:
        # 4. Si no existe (o lo acabamos de borrar), lo crea en Stripe
        try:
            stripe_customer = stripe.Customer.create(
                email=user.email if user.email else None,  # Asegurarse de que el email no es None
                name=user.username,
                description=f"Cliente Django (ID: {user.id})"
            )
            customer = Customer.objects.create(
                user=user,
                stripe_customer_id=stripe_customer.id
            )
            return customer.stripe_customer_id

        except stripe.StripeError as e:
            logger.error(f"Error creando Customer en Stripe para user {user.id}: {e}")
            raise


class PaymentMethodListCreateAPIView(generics.ListCreateAPIView):
    """
    Corresponde a:
    - GET /api/v1/payment-methods/ (Listar)
    - POST /api/v1/payment-methods/ (Añadir)
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AddPaymentMethodRequestSerializer
        return PaymentMethodSerializer

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['token']
        make_default = serializer.validated_data['make_default']
        user = request.user

        try:
            customer_id = get_or_create_stripe_customer(user)

            # 1. Adjuntamos el token al cliente. ESTO "gasta" el token.
            attached_pm = stripe.PaymentMethod.attach(token, customer=customer_id)

            # 2. Si es default, usamos el ID del OBJETO ADJUNTO (attached_pm.id)
            if make_default:
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={'default_payment_method': attached_pm.id},
                )

            with transaction.atomic():
                new_pm = PaymentMethod.objects.create(
                    user=user,
                    payment_method_id=f"pm_{user.id}_{attached_pm.card.last4}",
                    psp_ref=attached_pm.id,  # <-- Usamos el ID permanente
                    brand=attached_pm.card.brand,
                    last4=attached_pm.card.last4,
                    exp_mm=attached_pm.card.exp_month,
                    exp_yy=attached_pm.card.exp_year,
                    is_default=make_default,
                )
                if make_default:
                    PaymentMethod.objects.filter(user=user).exclude(pk=new_pm.pk).update(is_default=False)

            response_serializer = PaymentMethodSerializer(new_pm)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except stripe.StripeError as e:
            return Response({"error": e.user_message or str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentMethodDestroyAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = 'payment_method_id'

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        try:
            stripe.PaymentMethod.detach(instance.psp_ref)
        except Exception as e:
            logger.warning(f"No se pudo des-adjuntar PM de Stripe: {e}")
        instance.delete()


class PaymentIntentCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentIntentRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order_id = serializer.validated_data['order_id']
        pm_internal_id = serializer.validated_data['payment_method_id']
        user = request.user

        try:
            order = Order.objects.get(order_id=order_id, user=user, status=Order.OrderStatus.PENDING)
            pm = PaymentMethod.objects.get(payment_method_id=pm_internal_id, user=user)
            customer_id = get_or_create_stripe_customer(user)
            amount_in_cents = int(order.amount * 100)

            # Creamos el PaymentIntent USANDO el customer_id y el pm.psp_ref
            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=order.currency.lower(),
                customer=customer_id,
                payment_method=pm.psp_ref,  # El ID 'pm_...' permanente
                confirm=True,  # Intentar el pago ahora
                off_session=True,  # Indicar que el cliente no está presente
                description=f"Pago por Orden {order.order_id}",
                metadata={"order_id": str(order.order_id), "user_id": str(user.id)},
            )

            response_data = {
                "provider": "stripe",
                "client_secret": intent.client_secret,
                "payment_id": intent.id,
            }
            resp_ser = PaymentIntentResponseSerializer(data=response_data)
            resp_ser.is_valid(raise_exception=True)
            return Response(resp_ser.data, status=200)

        except Order.DoesNotExist:
            return Response({"error": "Orden no encontrada o ya procesada."}, status=404)
        except PaymentMethod.DoesNotExist:
            return Response({"error": "Método de pago no encontrado."}, status=404)

        except stripe.CardError as e:
            return Response({"error": e.user_message}, status=402)
        except stripe.InvalidRequestError as e:
            return Response({"error": e.user_message}, status=402)
        except stripe.StripeError as e:
            return Response({"error": "Error del proveedor de pago"}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        if not webhook_secret:
            logger.error("Webhook: STRIPE_WEBHOOK_SECRET no está configurada.")
            return Response({"error": "Webhook secret no configurado"}, status=500)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            logger.warning(f"Webhook (ValueError): {e}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.SignatureVerificationError as e:
            logger.warning(f"Webhook (SignatureError): {e}")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        event_type = event['type']
        event_data = event['data']

        if event_type == 'payment_intent.succeeded':
            logger.info("Webhook: Recibido 'payment_intent.succeeded'")
            handle_payment_intent_succeeded(event_data)
        elif event_type == 'payment_intent.payment_failed':
            logger.warning("Webhook: Recibido 'payment_intent.payment_failed'")
            handle_payment_intent_failed(event_data)
        else:
            logger.info(f"Webhook: Evento no manejado: {event_type}")

        return Response(status=status.HTTP_200_OK)