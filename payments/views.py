from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import stripe
import logging
from django.conf import settings
from .models import PaymentMethod
from .serializers import AddPaymentMethodRequestSerializer, PaymentMethodSerializer

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