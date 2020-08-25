from django.conf.urls import url
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator

from ghostwriter.oplog.consumers import OplogEntryConsumer

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
            URLRouter(
               [
                    path("ws/oplog/<int:pk>/entries", OplogEntryConsumer)
               ])
    )
})
