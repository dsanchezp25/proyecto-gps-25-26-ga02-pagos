from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from weasyprint import HTML
import logging

from .models import Order, OrderItem
from cart.models import ShoppingCart
from pricing.services import calculate_cart_totals

# Configurar un logger
logger = logging.getLogger(__name__)

def generate_invoice_pdf(order: Order):
    """
    Renderiza la plantilla HTML de la factura y la convierte en un PDF
    Guarda el PDF en el campo invoice_pdf del pedido
    """
    try:
        # 1. Renderizar la plantilla HTML
        html_string = render_to_string('invoices/invoice.html', {'order': order})
        # 2. Convertir HTML a PDF en memoria
        pdf_file = HTML(string=html_string).write_pdf()
        # 3. Crear un nombre de fichero
        filename = f'factura_{order.order_id}.pdf'
        # 4. Guardar el PDF en el campo FileField del pedido
        order.invoice_pdf.save(filename, ContentFile(pdf_file), save=True)

        logger.info(f"Factura PDF generada y guardada para el pedido {order.order_id}")
    except Exception as e:
        logger.error(f"Error al generar la factura PDF para el pedido {order.order_id}: {e}")

def create_order_from_cart(user, region_code: str = None) -> Order:
    """
    Servicio principal para "realizar la compra"
    Convierte un carrito en un pedido y genera la factura PDF
    """
    try:
        # 1. Obtener el carrito activo del usuario
        cart = ShoppingCart.objects.get(user=user, status=Order.Status.ACTIVE)
        cart_items = cart.items.all()

        if not cart_items:
            raise ValueError("El carrito está vacío")

        # 2. Obtener los totales calculados
        totals = calculate_cart_totals(cart, region_code)

        # 3. Pago

        # 4 . Crear el pedido
        order = Order.objects.create(
            user=user,
            status=Order.OrderStatus.COMPLETED,
            subtotal=totals['subtotal'],
            tax_total=totals['tax_amount'],
            tax_percentage=totals['tax_percentage'],
            tax_name=totals['tax_rate_name'],
            total_paid=totals['total']
        )

        # 5. Copiar los articulos del carrito al pedido
        order_items_to_create = []
        for item in cart_items:
            order_items_to_create.append(
                OrderItem(
                    order=order,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=item.price_at_addition
                )
            )
        OrderItem.objects.bulk_create(order_items_to_create)

        # 6. Generar la factura PDF
        generate_invoice_pdf(order)

        # 7. Marcar el carrito como completado
        cart.status = ShoppingCart.Status.COMPLETED
        cart.save()

        return order

    except ShoppingCart.DoesNotExist:
        logger.warning(f"Intento de compra sin carrito activo para usuario {user.id}")
        raise ValueError("No se encontró un carrito activo.")
    except Exception as e:
        logger.error(f"Error al crear el pedido para usuario {user.id}: {e}")
        # Si el pago falló, marcar como FAILED
        # Order.objects.create(user=user, status=Order.OrderStatus.FAILED, ...)
        raise