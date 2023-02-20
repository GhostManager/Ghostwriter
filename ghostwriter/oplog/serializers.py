"""This contains all the serializers used by the Oplog application's REST API."""

# 3rd Party Libraries
from rest_framework import serializers

# Ghostwriter Libraries
from ghostwriter.oplog.models import Oplog, OplogEntry


class OplogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Oplog
        fields = "__all__"


class OplogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = OplogEntry
        fields = "__all__"
