from django.urls import NoReverseMatch
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import (
    View,
    ListView,
    FormView,
)
from django.urls import reverse_lazy
from admin.base.forms import GuidForm
from django.contrib.auth.mixins import PermissionRequiredMixin
from admin.base.views import GuidView
from osf.models import Guid, GuidMetadataRecord, BaseFileNode


class FileSearchView(PermissionRequiredMixin, FormView):
    """ Allows authorized users to search for a specific file by guid.
    """
    template_name = 'files/search.html'
    permission_required = 'osf.view_file'
    raise_exception = True
    form_class = GuidForm

    def form_valid(self, form):
        guid = form.cleaned_data['guid']
        if guid:
            try:
                return redirect(reverse_lazy('files:file', kwargs={'guid': guid}))
            except NoReverseMatch as e:
                messages.error(self.request, str(e))
        return super().form_valid(form)


class FileMixin(PermissionRequiredMixin):

    def get_object(self):
        target_file = Guid.load(self.kwargs['guid']).referent
        return target_file

    def get_success_url(self):
        return reverse_lazy('files:file', kwargs={'guid': self.kwargs['guid']})


class FileView(FileMixin, GuidView):
    """ Allows authorized users to view file info."""
    template_name = 'files/file.html'
    permission_required = 'osf.view_file'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        guid = self.kwargs['guid']
        metadata_record = GuidMetadataRecord.objects.for_guid(
            guid,
            allowed_referent_models=(BaseFileNode,),
        )
        file = context['object']
        node = file.target
        latest_modified = file.versions.latest('created')
        context.update({
            'guid': guid,
            'node_id': node._id if node else None,
            'node': node,
            'file_metadata': metadata_record,
            'version': latest_modified.location.get('version', '')
        })
        return context
