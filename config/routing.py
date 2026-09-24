# WebSocket routes, the ws:// equivalent of urls.py.
from django.urls import path
from pos.consumers import KitchenConsumer, TableOrderConsumer, TablesConsumer

websocket_urlpatterns = [
    path("ws/kitchen/", KitchenConsumer.as_asgi()),                          # kitchen display feed
    path("ws/tables/", TablesConsumer.as_asgi()),                            # tables overview feed
    path("ws/table/<slug:zone>/<int:table>/", TableOrderConsumer.as_asgi()), # single table order feed
]
