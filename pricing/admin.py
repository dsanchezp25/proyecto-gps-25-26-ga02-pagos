from django.contrib import admin
from .models import TaxRate, RegionTaxRule

@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ('name', 'rate')

@admin.register(RegionTaxRule)
class RegionTaxRuleAdmin(admin.ModelAdmin):
    list_display = ('region_code', 'tax_rate')