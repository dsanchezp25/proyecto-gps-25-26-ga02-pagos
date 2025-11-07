import uuid
from django.db import models
from django.conf import settings

class Order(models.Model):
    """
    Representa un pedido completo
    Esto es lo que se convierte en factura
    """
    class OrderStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        COMPLETED = 'COMPLETED', 'Completado'
        FAILED = 'FAILED', 'Fallido'
        REFUNED = 'REFUNED', 'Reembolsado'

    order_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=10,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING
    )

    # ----- Detalles de pago -----

    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='EUR')

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    tax_name = models.CharField(max_length=100, default="N/A")
    total_paid = models.DecimalField(max_digits=10, decimal_places=2)

    invoice_pdf = models.FileField(upload_to='invoices/%Y/%m/%d', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __dir__(self):
        return f"Pedido {self.order_id} - Usuario: {self.user.username} - Estado: {self.status}"


class OrderItem(models.Model):
    """
    Los articulos dentro de un pedido
    """
    class ItemType(models.TextChoices):
        ALBUM = 'ALBUM', 'Álbum'
        TRACK = 'TRACK', 'Canción'
        SUB = 'SUB', 'Suscripción'

    item_type = models.CharField(
        max_length=10,
        choices=ItemType.choices,
        help_text="Precio por unidad en el momento de la compra",
        default=0.00
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items' )
    product_id = models.IntegerField()
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text='Unidad del producto')

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"Producto {self.product_id} - Cantidad: {self.quantity} - Precio Unitario: {self.unit_price}"

