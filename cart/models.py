from django.db import models
from django.conf import settings

class ShoppingCart(models.Model):
    """
        Modelo que representa el carrito de un usuario.
        Usamos OneToOneField para asegurar que cada usuario tenga un solo carrito.
    """
    class CartStatus(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        ORDERED = 'ordered', 'Ordenado'

    status = models.CharField(
        max_length=10,
        choices=CartStatus.choices,
        default=CartStatus.ACTIVE
    )


    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito de {self.user.username}"

class CartItem(models.Model):
    """
        Modelo que representa un ítem dentro del carrito de compras
    """
    # Relación al carrito al que pertenece este ítem
    cart = models.ForeignKey(
        ShoppingCart,
        on_delete=models.CASCADE,
        related_name='items'
    )

    # ID del producto
    # No es una ForeignKey, es solo ID
    product_id = models.PositiveIntegerField()

    quantity = models.PositiveIntegerField(default=1)

    # Guardamos el precio en el momento de agregar al carrito
    price_at_addition = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio del producto al momento de agregar al carrito"
    )

    class Meta:
        # Evita duplicados del mismo producto en el carrito
        unique_together = ('cart', 'product_id')

    def __str__(self):
        return f"CartItem {self.cart.user.username} {self.product_id}"