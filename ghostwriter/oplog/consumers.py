"""This contains all the WebSocket consumers used by the Oplog application."""

# Standard Libraries
import json
import logging
from copy import deepcopy
from datetime import datetime
from functools import reduce

# Django Imports
from django.db.models import TextField, Func, Subquery, OuterRef, Value, F
from django.db.models.functions import Cast, Left
from django.db.models.expressions import CombinedExpression
from django.utils.timezone import make_aware
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, SearchVectorField

# 3rd Party Libraries
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework.utils.serializer_helpers import ReturnList
from taggit.models import TaggedItem

# Ghostwriter Libraries
from ghostwriter.api.utils import verify_access
from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.modules.custom_serializers import OplogEntrySerializer
from ghostwriter.oplog.models import Oplog, OplogEntry
from ghostwriter.users.models import User

# Using __name__ resolves to ghostwriter.oplog.consumers
logger = logging.getLogger(__name__)


class TsVectorConcat(Func):
    """
    Raw concat operator.

    Unlike Django's built in Concat function, this does not convert each argument to text first, so
    it can be used with tsvectors.
    """

    template = "(%(expressions)s)"
    arg_joiner = " || "
    output_field = SearchVectorField()


@database_sync_to_async
def create_oplog_entry(oplog_id, user):
    """Attempt to create a new log entry for the given log ID."""
    try:
        oplog = Oplog.objects.get(pk=oplog_id)
    except Oplog.DoesNotExist:
        logger.warning("Failed to create log entry for log ID %s because that log ID does not exist.", oplog_id)
        return

    if verify_access(user, oplog.project):
        OplogEntry.objects.create(
            oplog_id_id=oplog_id, operator_name=user.username, extra_fields=ExtraFieldSpec.initial_json(OplogEntry)
        )
    else:
        logger.warning(
            "User %s attempted to create a log entry for log ID %s without permission.", user.username, oplog_id
        )


@database_sync_to_async
def delete_oplog_entry(entry_id, user):
    """Attempt to delete the log entry with the given entry ID."""
    try:
        entry = OplogEntry.objects.get(pk=entry_id)
        if verify_access(user, entry.oplog_id.project):
            entry.delete()
        else:
            logger.warning(
                "User %s attempted to delete log entry %s for log ID %s without permission.",
                user.username,
                entry_id,
                entry.oplog_id.id,
            )
    except OplogEntry.DoesNotExist:
        # This is fine, it just means the entry was already deleted
        pass


@database_sync_to_async
def copy_oplog_entry(entry_id, user):
    """Attempt to copy the log entry with the given entry ID."""
    try:
        entry = OplogEntry.objects.get(pk=entry_id)
    except OplogEntry.DoesNotExist:
        logger.warning("Failed to copy log entry %s because that entry ID does not exist.", entry_id)
        return

    if verify_access(user, entry.oplog_id.project):
        copy = deepcopy(entry)
        copy.pk = None
        copy.start_date = make_aware(datetime.utcnow())
        copy.end_date = make_aware(datetime.utcnow())
        copy.save()
        copy.tags.add(*entry.tags.all())
    else:
        logger.warning(
            "User %s attempted to copy log entry %s for log ID %s without permission.",
            user.username,
            entry_id,
            entry.oplog_id.id,
        )


class OplogEntryConsumer(AsyncWebsocketConsumer):
    """This consumer handles WebSocket connections for :model:`oplog.OplogEntry`."""

    @database_sync_to_async
    def get_log_entries(self, oplog_id: int, offset: int, user: User, filter: str | None = None) -> ReturnList:
        try:
            oplog = Oplog.objects.get(pk=oplog_id)
        except Oplog.DoesNotExist:
            logger.warning("Failed to get log entries for log ID %s because that log ID does not exist.", oplog_id)
            return OplogEntrySerializer([], many=True).data

        if not verify_access(user, oplog.project):
            return OplogEntrySerializer([], many=True).data

        entries = OplogEntry.objects.filter(oplog_id=oplog_id)
        if filter:
            # Build search vectors.
            # english_vector_args should contain fields containing mostly English text, and will be stemmed.
            # simple_vector_args should contain fields that won't be stemmed.

            # Built-in fields
            english_vector_args = [
                "description",
                "output",
                "comments",
            ]

            simple_vector_args = english_vector_args + [
                "entry_identifier",
                "source_ip",
                "dest_ip",
                "tool",
                "user_context",
                "command",
                "operator_name",
                "start_date",
                "end_date",
            ]

            # Subquery to fetch tags
            simple_vector_args.append(
                Subquery(
                    TaggedItem.objects.filter(
                        content_type__app_label=OplogEntry._meta.app_label,
                        content_type__model=OplogEntry._meta.model_name,
                        object_id=OuterRef("pk"),
                    )
                    .annotate(all_tags=Func(F("tag__name"), Value(" "), function="STRING_AGG"))
                    .values("all_tags")
                )
            )

            # JSON operations to fetch extra fields
            for spec in ExtraFieldSpec.objects.filter(target_model=OplogEntry._meta.label):
                if spec.type == "json":
                    continue

                field = CombinedExpression(
                    F("extra_fields"),
                    "->>",
                    Value(spec.internal_name),
                )
                simple_vector_args.append(field)
                if spec.type == "rich_text":
                    english_vector_args.append(field)

            # Create and combine search vectors.
            # Limit inputs since PostgreSQL will abort the query if attempting to make a tsvector out of a huge string
            vectors = [SearchVector(Left(Cast(va, TextField()), 100000), config="english") for va in english_vector_args] + \
                [SearchVector(Left(Cast(va, TextField()), 100000), config="simple") for va in simple_vector_args]
            vector = TsVectorConcat(*vectors)

            # Build filter.
            # Search using both english and simple configs, to help match both types of vectors. Also use prefix
            # terms to help search partial matches.

            def q_term(term):
                term = "'" + term.replace("'", "''").replace("\\", "\\\\") + "':*"
                return SearchQuery(term, config="english", search_type="raw") | SearchQuery(
                    term, config="simple", search_type="raw"
                )

            query = reduce(lambda a, b: a & b, (q_term(term) for term in filter.split()))

            # Run query
            entries = (
                entries.annotate(
                    search=vector,
                    rank=SearchRank(vector, query),
                )
                .filter(search=query)
                .order_by("-start_date")
            )
        else:
            entries = entries.order_by("-start_date")
        entries = entries[offset : offset + 100]
        return OplogEntrySerializer(entries, many=True).data

    async def send_oplog_entry(self, event):
        await self.send(text_data=event["text"])

    async def connect(self):
        user = self.scope["user"]
        if user.is_active:
            oplog_id = self.scope["url_route"]["kwargs"]["pk"]
            await self.channel_layer.group_add(str(oplog_id), self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        logger.info("WebSocket disconnected with close code: %s", close_code)

    async def receive(self, text_data=None, bytes_data=None):
        user = self.scope["user"]
        json_data = json.loads(text_data)
        if json_data["action"] == "delete":
            oplog_entry_id = int(json_data["oplogEntryId"])
            await delete_oplog_entry(oplog_entry_id, user)

        if json_data["action"] == "copy":
            oplog_entry_id = int(json_data["oplogEntryId"])
            await copy_oplog_entry(oplog_entry_id, user)

        if json_data["action"] == "create":
            await create_oplog_entry(json_data["oplog_id"], self.scope["user"])

        if json_data["action"] == "sync":
            oplog_id = json_data["oplog_id"]
            offset = json_data["offset"]
            filter = json_data.get("filter", "")
            entries = await self.get_log_entries(oplog_id, offset, user, filter)
            message = json.dumps(
                {
                    "action": "sync",
                    "filter": filter,
                    "offset": offset,
                    "data": entries,
                }
            )

            await self.send(text_data=message)
