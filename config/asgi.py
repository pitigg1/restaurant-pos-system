import os
import django

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

import config.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

django_asgi_app = get_asgi_application()

# Makes /static/ work under ASGI/Channels (runserver's WSGI static serving
# doesn't apply here since Daphne handles everything).
django_asgi_app = ASGIStaticFilesHandler(django_asgi_app)

# Dispatches by protocol: plain HTTP vs WebSocket connections.
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(config.routing.websocket_urlpatterns)
    ),
})