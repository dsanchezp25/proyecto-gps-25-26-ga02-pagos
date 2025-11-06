from decimal import Decimal
from .models import RegionTaxRule, TaxRate

# Define un impuesto por defecto si no se encuentra la región
# Sería bueno crear esta entrada en tu BBDD de admin
DEFAULT_TAX_RATE = TaxRate(name="IVA General", rate=Decimal("21.00"))
DEFAILT_REGION_CODE = "ES"

def get_tax_rate_for_region(region_code: str) -> TaxRate:
    """
    Busca en la BBDD la regla de un impuesto para una región
    Si no la encuentra, usa la regla por defecto
    """
    try:
        # Busca la regla especifica
        rule = RegionTaxRule.objects.select_related('tax_rate').get(region_code=region_code)
        return rule.tax_rate
    except RegionTaxRule.DoesNotExist:
        # Si no existe, devuelve la regla por defecto
        try:
            default_rule = RegionTaxRule.objects.select_related('tax_rate').get(region_code=DEFAILT_REGION_CODE)
            return default_rule.tax_rate
        except RegionTaxRule.DoesNotExist:
            return DEFAULT_TAX_RATE

def calculate_cart_totals(cart, region_code: str = None):
    """
    Servicio principal que calcula los totales de un carrito
    """
    # 1. Calcular subtotal
    subtotal = Decimal("0.00")
    items = cart.items.all()
    if not items:
        # Carrito vacío
        return {
            "subtotal": Decimal("0.00"),
            "tax_rate_name": "N/A",
            "tax_rate_percent": Decimal("0.00"),
            "tax_amount": Decimal("0.00"),
            "total": Decimal("0.00")
        }

    for item in items:
        subtotal += item.price_at_addition * item.quantity

    # 2. Obtener region del usuario
    if region_code is None:
        # Si no nos pasan región, intentamos obtenerla del perfil del usuario
        try:
            # TODO: Cambiar 'profile.region_code' por el campo real del perfil de usuario
            region_code = cart.user.profile.region_code
        except AttributeError:
            # Si no hay usuario o perfil, usar región por defecto
            region_code = DEFAILT_REGION_CODE
    # 3. Otener tasa de impuesto
    tax_rate = get_tax_rate_for_region(region_code)

    # 4. Calcular impuesto y total
    tax_amount = (subtotal * tax_rate.rate) / Decimal("100.00")
    total = subtotal + tax_amount

    # 5. Devolver resultados
    return {
        "subtotal": subtotal.quantize(Decimal("0.01")),
        "tax_rate_name": tax_rate.name,
        "tax_rate_percent": tax_rate.rate.quantize(Decimal("0.01")),
        "tax_amount": tax_amount.quantize(Decimal("0.01")),
        "total": total.quantize(Decimal("0.01"))
    }