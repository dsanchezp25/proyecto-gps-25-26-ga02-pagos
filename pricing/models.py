from django.db import models

class TaxRate(models.Model):
    """
    Representa un tipo de impuesto y su porcentaje asociado.
    """
    name = models.CharField(max_length=100, unique=True)
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="El porcentaje de impuesto"
    )

    def __str__(self):
        return f"{self.name} ({self.rate}%)"

class RegionTaxRule(models.Model):
    """
    Tabla de configuración que vincula una región a un impuesto
    Permite "actualizzción sin modificar el código"
    """
    region_code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Codigo de region"
    )
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.PROTECT)

    def __str__(self):
        return f"Regla para {self.region_code}: {self.tax_rate}"