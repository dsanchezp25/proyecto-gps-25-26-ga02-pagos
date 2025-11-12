import stripe
import logging
from decimal import Decimal
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from weasyprint import HTML
from django.db import transaction

from orders.models import Order, Invoice  # <-- ¡Importar Invoice!

logger = logging.getLogger(__name__)


def generate_invoice_pdf_for_order(order: Order):
    """
    Genera el PDF y crea el objeto Invoice.
    (Esta es la lógica que movimos de 'orders/services.py')
    """
    try:
        html_string = render_to_string('invoices/invoice.html', {'order': order})
        pdf_file = HTML(string=html_string).write_pdf()
        filename = f'factura_{order.order_id}.pdf'

        # Crear el objeto Invoice y guardar el fichero
        invoice = Invoice(order=order)
        invoice.invoice_pdf.save(filename, ContentFile(pdf_file), save=True)

        logger.info(f"Factura PDF generada y guardada para Pedido {order.order_id}")
        return invoice

    except Exception as e:
        logger.error(f"Error al generar PDF para Pedido {order.order_id}: {e}")
        raise


def handle_payment_intent_succeeded(event_data):
    """
    Lógica para el evento 'payment_intent.succeeded'.
    Marca la orden como pagada y genera la factura.
    """
    payment_intent = event_data['object']
    payment_id = payment_intent['id']
    amount_received = Decimal(payment_intent['amount_received']) / 100

    # En un proyecto real, buscaríamos la 'order_id' en los 'metadata'
    # del payment_intent, que habríamos añadido en el Paso 21.

    # --- SIMULACIÓN (buscar por importe) ---
    # Esto es peligroso en producción, pero vale para probar.
    try:
        with transaction.atomic():
            # Buscamos la orden PENDIENTE que coincida con el importe
            order = Order.objects.select_for_update().get(
                amount=amount_received,
                status=Order.OrderStatus.PENDING
            )

            # 1. Marcar la orden como Pagada
            order.status = Order.OrderStatus.PAID
            order.save()

            # 2. Generar la factura PDF
            generate_invoice_pdf_for_order(order)

            logger.info(f"Webhook: Pedido {order.order_id} marcado como PAGADO.")

    except Order.DoesNotExist:
        logger.error(
            f"Webhook: No se encontró Pedido PENDIENTE para PaymentIntent {payment_id} con importe {amount_received}")
    except Exception as e:
        logger.error(f"Webhook: Error al procesar Pedido para PaymentIntent {payment_id}: {e}")
        raise  # Falla el webhook para que Stripe reintente


def handle_payment_intent_failed(event_data):
    """
    Lógica para el evento 'payment_intent.payment_failed'.
    Marca la orden como Fallida.
    """
    payment_intent = event_data['object']
    # TODO: Buscar la orden asociada
    logger.warning(
        f"Webhook: Pago fallido {payment_intent['id']}. Razón: {payment_intent['last_payment_error']['message']}")
    # order.status = Order.OrderStatus.FAILED
    # order.save(