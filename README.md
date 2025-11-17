# 💳 Microservicio de Pagos y Facturación (Django)

Este microservicio gestiona el ciclo completo de compra: carrito, cálculo de impuestos, creación de pedidos, procesamiento de pagos con Stripe (con soporte para 3D Secure y Clientes) y generación automática de facturas en PDF.

---

## 🛠️ Requisitos Previos

1.  **Python 3.10+**
2.  **Stripe CLI** (Para probar webhooks localmente).
3.  **GTK3 Runtime (Solo Windows):** Necesario para generar PDFs con `WeasyPrint`.
    * Descargar e instalar: [GTK3 Installer for Windows](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) (Reiniciar tras instalar).

---

## 🚀 Instalación y Configuración

### 1. Configurar Entorno
```bash
# Clonar el repositorio (si no lo tienes)
git clone <url-del-repo>
cd proyecto-gps-25-26-ga02-pagos

# Crear y activar entorno virtual
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2\. Configurar Variables (Stripe)

Asegúrate de tener tus claves de prueba de Stripe en `proyecto_gps_25_26_ga02_pagos/settings.py`:

```python
STRIPE_PUBLIC_KEY = "pk_test_..."
STRIPE_SECRET_KEY = "sk_test_..."
STRIPE_WEBHOOK_SECRET = "whsec_..." # (Se obtiene al ejecutar 'stripe listen')
```

### 3\. Base de Datos y Admin

```bash
# Aplicar migraciones (Cart, Orders, Payments, Pricing)
python manage.py migrate

# Crear superusuario para acceder al Admin y API Navegable
python manage.py createsuperuser
```

-----

## 📚 Documentación de la API

El proyecto expone una API REST bajo `/api/v1/`.

### 🛒 Carrito de Compra (`cart`)

  * **GET** `http://127.0.0.1:8000/api/v1/cart/`: Ver carrito actual y totales calculados (con impuestos).
  * **POST** `http://127.0.0.1:8000/api/v1/cart/items/`: Añadir producto.
    ```json
    { "product_id": 101, "quantity": 2, "price_at_addition": "50.00" }
    ```
  * **DELETE** `http://127.0.0.1:8000/api/v1/cart/items/{id}/`: Eliminar producto.

### 📦 Pedidos (`orders`)

  * **POST** `http://127.0.0.1:8000/api/v1/orders/`: Checkout. Convierte el carrito activo en un Pedido (`PENDING`).
    ```json
    {}
    ```
  * **GET** `http://127.0.0.1:8000/api/v1/orders/{uuid}/`: Ver detalles del pedido.

### 💳 Pagos y Tarjetas (`payments`)

  * **POST** `http://127.0.0.1:8000/api/v1/payment-methods/`: Guardar tarjeta (Crea Cliente en Stripe).
    ```json
    { "provider": "stripe", "token": "pm_card_visa", "make_default": true }
    ```
  * **POST** `http://127.0.0.1:8000/api/v1/payments/intent/`: Iniciar cobro.
    ```json
    { "order_id": "uuid-del-pedido", "payment_method_id": "pm_interno" }
    ```
    * **IMPORTANTE:** Copia el pm_interno del pedido generado  y reemplaza `payment_method_id` en el comando.
    * **IMPORTANTE:** Copia el uuid del pedido generado en el paso 3 y reemplaza `uuid-del-pedido` en el comando.
  * **POST** `http://127.0.0.1:8000/api/v1/webhooks/stripe`: Endpoint para recibir eventos de Stripe.

-----

## 🧪 Guía de Pruebas (Flujo Completo)

Para probar el sistema de pagos real, necesitamos simular la conexión con Stripe.

### Paso 1: Preparar el Servidor (3 Terminales)

1.  **Terminal 1 (Django):**

    ```bash
    python manage.py runserver
    ```

2.  **Terminal 2 (Stripe Listen - Webhook):**

    ```bash
    .\stripe.exe listen --forward-to http://127.0.0.1:8000/api/v1/webhooks/stripe/
    ```

      * **IMPORTANTE:** Copia el `whsec_...` que aparece, pégalo en `proyecto_gps_25_26_ga02_pagos/settings.py` y **reinicia la Terminal 1**.

3.  **Terminal 3 (Stripe Trigger):** Déjala lista para el paso final.
    
    ```bash    
    .\stripe.exe trigger payment_intent.succeeded --add payment_intent:metadata.order_id=TU_UUID_DEL_PEDIDO
    ```
    * **IMPORTANTE:** Copia el uuid del pedido generado en el paso 3 y reemplaza `TU_UUID_DEL_PEDIDO` en el comando.

### Paso 2: Configuración Inicial (Navegador)

1.  Ve a `http://127.0.0.1:8000/admin/`.
2.  En **Pricing**, añade un `TaxRate` (ej. IVA 21%) y una `RegionTaxRule` (ej. ES -\> IVA).
3.  *(Opcional)* Borra pedidos/carritos antiguos para probar limpio.

### Paso 3: Ejecutar el Flujo

1.  **Llenar Carrito:** POST a `/api/v1/cart/items/`.
2.  **Checkout:** POST a `/api/v1/orders/`. Copia el `order_id`.
3.  **Añadir Tarjeta:** POST a `/api/v1/payment-methods/` con token `pm_card_visa`. Copia el `payment_method_id`.
4.  **Pagar:** POST a `/api/v1/payments/intent/` con los dos IDs.
      * Debe devolver `200 OK` y un `client_secret`.

### Paso 4: Simular Pago Exitoso

En la **Terminal 3**, ejecuta este comando reemplazando el UUID por el de tu pedido:

```bash
stripe trigger payment_intent.succeeded --add payment_intent:metadata.order_id=TU_UUID_DEL_PEDIDO
```

### ✅ Resultado Esperado

1.  En **Terminal 1**, verás: `Webhook: Pedido ... marcado como PAGADO` y `Factura PDF generada`.
2.  En el **Admin**, el pedido pasará a estado **PAID**.
3.  En el **Admin \> Invoices**, podrás descargar la factura PDF.

-----

## ✅ Tests Automáticos

El proyecto incluye tests unitarios robustos que "engañan" (mock) a Stripe para no hacer llamadas reales durante el desarrollo.

```bash
python manage.py test
```

Resultado esperado: `OK` (Todos los tests de cart, orders y payments pasando).
