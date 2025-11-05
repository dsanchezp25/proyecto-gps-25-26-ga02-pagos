"""
ASGI config for proyecto_gps_25_26_ga02_pagos project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_gps_25_26_ga02_pagos.settings')

application = get_asgi_application()
