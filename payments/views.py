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
from .models import PaymentMethod
from .serializers import (
    AddPaymentMethodRequestSerializer,
    PaymentMethodSerializer,
    PaymentIntentRequestSerializer,
    PaymentIntentResponseSerializer,
)
from orders.models import Order
from .services import handle_payment_intent_failed, handle_payment_intent_succeeded

# Configurar Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


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
        # GET: Devuelve solo los métodos del usuario autenticado
        return PaymentMethod.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        # POST: Añade un nuevo método de pago
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['token']
        make_default = serializer.validated_data['make_default']
        user = request.user

        try:
            # 1. Obtenemos los detalles de la tarjeta desde Stripe
            # Esto nos da el 'last4', 'brand', 'exp_month', 'exp_year'
            pm = stripe.PaymentMethod.retrieve(token)

            # 2. (Opcional) Adjuntamos el método de pago al Customer de Stripe
            # customer_id = user.profile.stripe_customer_id
            # stripe.PaymentMethod.attach(token, customer=customer_id)

            # 3. Guardamos los metadatos (¡nunca el CVV o el nº completo!)
            new_pm = PaymentMethod.objects.create(
                user=user,
                payment_method_id=f"pm_{user.id}_{pm.card.last4}",  # ID interno simple
                psp_ref=pm.id,  # El 'pm_...' de Stripe
                brand=pm.card.brand,
                last4=pm.card.last4,
                exp_mm=pm.card.exp_month,
                exp_yy=pm.card.exp_year,
                is_default=make_default,
            )

            # Si es el nuevo default, quitamos el default anterior
            if make_default:
                PaymentMethod.objects.filter(user=user).exclude(pk=new_pm.pk).update(is_default=False)

            response_serializer = PaymentMethodSerializer(new_pm)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except stripe.error.StripeError as e:
            logger.error(f"Error de Stripe al añadir PM: {e}")
            return Response({"error": "Error del proveedor de pago"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error interno al añadir PM: {e}")
            return Response({"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentMethodDestroyAPIView(generics.DestroyAPIView):
    """
    Corresponde a: DELETE /api/v1/payment-methods/{pm_id}/
    """
    permission_classes = [IsAuthenticated]
    lookup_field = 'payment_method_id'  # Usamos nuestro ID interno (pm_abc)

    def get_queryset(self):
        # Solo permite borrar métodos del propio usuario
        return PaymentMethod.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        # TODO: Des-adjuntar el método del Customer en Stripe
        # try:
        #    stripe.PaymentMethod.detach(instance.psp_ref)
        # except Exception as e:
        #    logger.warning(f"No se pudo des-adjuntar PM de Stripe: {e}")

        instance.delete()


class PaymentIntentCreateAPIView(APIView):
    """
        Corresponde a: POST /api/v1/payments/intent
        Crea una "intención de pago" en el PSP (Stripe).
        """
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentIntentRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        order_id = validated_data['order_id']
        payment_method_id = validated_data['payment_method_id']  # ID interno (pm_abc)
        user = request.user

        try:
            # 1. Validar que la Orden existe y es del usuario
            order = Order.objects.get(
                order_id=order_id,
                user=user,
                status=Order.OrderStatus.PENDING
            )

            # 2. Validar que el Método de Pago existe y es del usuario
            payment_method = PaymentMethod.objects.get(
                payment_method_id=payment_method_id,
                user=user
            )

            # 3. Convertir el 'amount' (Decimal) a céntimos (integer) para Stripe
            amount_in_cents = int(order.amount * 100)

            # 4. Crear el Payment Intent en Stripe
            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=order.currency.lower(),
                customer=None,  # TODO: Añadir stripe_customer_id del perfil de usuario
                payment_method=payment_method.psp_ref,  # El 'pm_...' REAL de Stripe
                confirm=True,  # Intentamos confirmar el pago inmediatamente
                automatic_payment_methods={"enabled": True, "allow_redirects": "never"},  # Para pagos "off-session"
                description=f"Pago por Orden {order.order_id}",
            )

            # 5. Devolver el client_secret
            response_data = {
                "provider": "stripe",
                "client_secret": intent.client_secret,
                "payment_id": intent.id
            }
            response_serializer = PaymentIntentResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Orden no encontrada o ya procesada."}, status=status.HTTP_404_NOT_FOUND)
        except PaymentMethod.DoesNotExist:
            return Response({"error": "Método de pago no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except stripe.error.CardError as e:
            # El pago fue declinado por la tarjeta
            logger.warning(f"Pago (CardError) fallido para orden {order_id}: {e.user_message}")
            return Response({"error": e.user_message}, status=status.HTTP_402_PAYMENT_REQUIRED)
        except stripe.error.StripeError as e:
            logger.error(f"Error de Stripe al crear PaymentIntent: {e}")
            return Response({"error": "Error del proveedor de pago"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')  # Desactivar CSRF para este endpoint
class StripeWebhookAPIView(APIView):
    """
    Corresponde a: POST /api/v1/webhooks/stripe
    Recibe eventos de Stripe.
    """
    permission_classes = [AllowAny]  # Stripe no envía token de autenticación

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            # 1. Verificar la firma de Stripe
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            # Payload inválido
            logger.warning(f"Webhook (ValueError): {e}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            # Firma inválida
            logger.warning(f"Webhook (SignatureError): {e}")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # 2. Obtener los datos del evento
        event_type = event['type']
        event_data = event['data']

        # 3. Manejar el evento
        if event_type == 'payment_intent.succeeded':
            logger.info("Webhook: Recibido 'payment_intent.succeeded'")
            handle_payment_intent_succeeded(event_data)

        elif event_type == 'payment_intent.payment_failed':
            logger.warning("Webhook: Recibido 'payment_intent.payment_failed'")
            handle_payment_intent_failed(event_data)

        # ... (manejar otros eventos como 'subscription.updated', etc.)

        else:
            logger.info(f"Webhook: Evento no manejado: {event_type}")

        # 4. Devolver 200 a Stripe para confirmar recepción
        return Response(status=status.HTTP_200_OK)