# Duplicate of config/routing.py; not imported anywhere (asgi.py uses
# config.routing instead). Kept here, seemingly unused.
from django.urls import path
from pos.consumers import KitchenConsumer, TableOrderConsumer, TablesConsumer

websocket_urlpatterns = [
    path("ws/kitchen/", KitchenConsumer.as_asgi()),
    path("ws/tables/", TablesConsumer.as_asgi()),
    path("ws/table/<slug:zone>/<int:table>/", TableOrderConsumer.as_asgi()),
]
