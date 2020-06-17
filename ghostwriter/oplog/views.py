from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from rest_framework import viewsets

from .models import Oplog, OplogEntry
from .forms import OplogCreateForm, OplogCreateEntryForm
from .serializers import OplogSerializer, OplogEntrySerializer

# Create your views here.
@login_required
def index(request):
	op_logs = Oplog.objects.all()
	context = {'op_logs' : op_logs}	
	return render(request, 'oplog/oplog_list.html', context=context)

@login_required
def OplogListEntries(request, pk):
	entries = OplogEntry.objects.filter(oplog_id=pk).order_by('-start_date')
	name = Oplog.objects.get(pk=pk).name
	context = {'entries':entries, 'pk':pk, 'name':name}
	return render(request, 'oplog/entries_list.html', context=context)


class OplogCreateWithoutProject(LoginRequiredMixin, CreateView):
	model = Oplog
	form_class = OplogCreateForm

	def get_success_url(self):
		return reverse('oplog:index')

class OplogEntryCreate(LoginRequiredMixin, CreateView):
	model = OplogEntry
	form_class = OplogCreateEntryForm

	def get_success_url(self):
		return reverse('oplog:oplog_entries', args=(self.object.oplog_id.id,))

class OplogEntryUpdate(LoginRequiredMixin, UpdateView):
	"""View for updating existing oplog entries. This view defaults to the
	oplogentry_form.html template.
	"""
	model = OplogEntry
	fields = '__all__'

	def get_success_url(self):
		"""Override the function to return to the new record after creation."""
		return reverse('oplog:oplog_entries', args=(self.object.oplog_id.id,))

class OplogEntryDelete(LoginRequiredMixin, DeleteView):
	"""View for deleting existing oplog entries. This view defaults to the
	oplogentry_form.html template.
	"""
	model = OplogEntry
	fields = '__all__'

	def get_success_url(self):
		"""Override the function to return to the new record after creation."""
		return reverse('oplog:oplog_entries', args=(self.object.oplog_id.id,))

class OplogEntryViewSet(viewsets.ModelViewSet):
    queryset = OplogEntry.objects.all()
    serializer_class = OplogEntrySerializer

class OplogViewSet(viewsets.ModelViewSet):
    queryset = Oplog.objects.all()
    serializer_class = OplogSerializer