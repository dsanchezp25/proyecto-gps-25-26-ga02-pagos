"""
WSGI config for proyecto_gps_25_26_ga02_pagos project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_gps_25_26_ga02_pagos.settings')

application = get_wsgi_application()
