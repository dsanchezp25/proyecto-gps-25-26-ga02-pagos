from django.urls import path
from .views import OrderListCreateAPIView, OrderRetrieveAPIView

app_name = "orders"

urlpatterns = [
    path(
        "orders/",
        OrderListCreateAPIView.as_view(),
        name="order-list-create",
    ),
    path(
        "orders/<uuid:order_id>/",
        OrderRetrieveAPIView.as_view(),
        name="order-retrieve",
    ),

]
