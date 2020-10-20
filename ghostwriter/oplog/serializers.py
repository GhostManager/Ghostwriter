"""This contains all of the serializers used by the Oplog application's REST API."""

# Django & Other 3rd Party Libraries
from rest_framework import serializers

from .models import Oplog, OplogEntry


class OplogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Oplog
        fields = "__all__"


class OplogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = OplogEntry
        fields = "__all__"
