"""
ASGI config for Ghostwriter project.

It exposes the ASGI callable as a module-level variable named ``application``.
For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/asgi/
"""
# Standard Libraries
import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

# This allows easy placement of apps within the interior ghostwriter directory
ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent
sys.path.append(str(ROOT_DIR / "ghostwriter"))


# If ``DJANGO_SETTINGS_MODULE`` is unset, default to the local settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

django_application = get_asgi_application()

# Import websocket application here, so apps from django_application are loaded first
import ghostwriter.home.routing  # noqa isort:skip
import ghostwriter.oplog.routing  # noqa isort:skip
import ghostwriter.reporting.routing  # noqa isort:skip

from channels.auth import AuthMiddlewareStack  # noqa isort:skip
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa isort:skip


application = ProtocolTypeRouter(
    {
        "http": django_application,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                ghostwriter.home.routing.websocket_urlpatterns
                + ghostwriter.oplog.routing.websocket_urlpatterns
                + ghostwriter.reporting.routing.websocket_urlpatterns
            )
        ),
    }
)

from config.websocket import websocket_application  # noqa isort:skip

# async def application(scope, receive, send):
#     if scope["type"] == "http":
#         await django_application(scope, receive, send)
#     elif scope["type"] == "websocket":
#         await websocket_application(scope, receive, send)
#     else:
#         raise NotImplementedError(f"Unknown scope type {scope['type']}")
