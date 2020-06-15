from django.urls import path

from .views import (
	index,
	OplogCreateWithoutProject,
	OplogEntryCreate,
	OplogEntryUpdate,
	OplogEntryDelete,
	OplogListEntries,
)

app_name = "oplog"

urlpatterns = [
		path('', index, name='index'),
		path('create/', OplogCreateWithoutProject.as_view(), name='oplog_create'),
		path('<int:pk>/entries/create', OplogEntryCreate.as_view(), name='oplog_entry_create'),
		path('<int:pk>/entries/update', OplogEntryUpdate.as_view(), name='oplog_entry_update'),
		path('<int:pk>/entries/delete', OplogEntryDelete.as_view(), name='oplog_entry_delete'),
		path('<int:pk>/entries', OplogListEntries, name='oplog_entries'),
	]




