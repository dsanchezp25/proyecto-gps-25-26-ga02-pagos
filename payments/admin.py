from django.contrib import admin
from .models import PaymentMethod, Customer

admin.site.register(PaymentMethod)
admin.site.register(Customer)