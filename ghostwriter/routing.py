"""This declares the protocol routing for Ghostwriter."""

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import ghostwriter.home.routing
import ghostwriter.oplog.routing

application = ProtocolTypeRouter(
    {
        # http->django views is added by default
        "websocket": AuthMiddlewareStack(
            URLRouter(ghostwriter.home.routing.websocket_urlpatterns +
                    ghostwriter.oplog.routing.websocket_urlpatterns)
        ),
    }
)
