import stripe
import logging
from decimal import Decimal
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from weasyprint import HTML
from django.db import transaction

from orders.models import Order, Invoice

logger = logging.getLogger(__name__)


def generate_invoice_pdf_for_order(order: Order):
    """
    Genera el PDF y crea el objeto Invoice.
    """
    try:
        html_string = render_to_string('invoices/invoice.html', {'order': order})
        pdf_file = HTML(string=html_string).write_pdf()
        filename = f'factura_{order.order_id}.pdf'

        invoice, _ = Invoice.objects.get_or_create(order=order)
        invoice.invoice_pdf.save(filename, ContentFile(pdf_file), save=True)

        logger.info(f"Factura PDF generada y guardada para Pedido {order.order_id}")
        return invoice
    except Exception as e:
        logger.error(f"Error al generar PDF para Pedido {order.order_id}: {e}")
        raise


def handle_payment_intent_succeeded(event_data):
    """
    Lógica para el evento 'payment_intent.succeeded'.
    Usa METADATA para encontrar la orden.
    """
    payment_intent = event_data['object']
    payment_id = payment_intent['id']

    # 1. Obtenemos la metadata que pusimos en la vista (views.py)
    metadata = payment_intent.get('metadata', {})
    order_id = metadata.get('order_id')

    if not order_id:
        logger.error(
            f"Webhook: 'payment_intent.succeeded' (ID: {payment_id}) no tiene 'order_id' en sus metadata. No se puede procesar.")
        return  # Salimos porque no podemos hacer nada

    try:
        with transaction.atomic():
            # 2. Buscamos la Orden por su ID exacto
            order = Order.objects.select_for_update().get(
                order_id=order_id,
                status=Order.OrderStatus.PENDING  # Solo procesamos las pendientes
            )

            # 3. Marcar la orden como Pagada
            order.status = Order.OrderStatus.PAID
            order.save()

            # 4. Generar la factura PDF
            generate_invoice_pdf_for_order(order)

            logger.info(f"Webhook: Pedido {order.order_id} (desde metadata) marcado como PAGADO.")

    except Order.DoesNotExist:
        logger.error(f"Webhook: No se encontró Pedido PENDIENTE con order_id {order_id} (PaymentIntent: {payment_id})")
    except Exception as e:
        logger.error(f"Webhook: Error al procesar Pedido {order_id}: {e}")
        raise


def handle_payment_intent_failed(event_data):
    payment_intent = event_data['object']
    metadata = payment_intent.get('metadata', {})
    order_id = metadata.get('order_id')

    if not order_id:
        logger.warning(f"Webhook: Pago fallido {payment_intent['id']} sin order_id.")
        return

    try:
        order = Order.objects.get(order_id=order_id, status=Order.OrderStatus.PENDING)
        order.status = Order.OrderStatus.FAILED
        order.save()
        logger.warning(f"Webhook: Pedido {order_id} marcado como FAILED.")
    except Order.DoesNotExist:
        logger.warning(f"Webhook: Pedido PENDIENTE {order_id} no encontrado para pago fallido.")