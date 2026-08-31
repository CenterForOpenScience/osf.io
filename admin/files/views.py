from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, View
from django.contrib.auth.mixins import PermissionRequiredMixin

from admin.base.forms import GuidForm
from admin.base.views import GuidView
from admin.files.tasks import purge_file_version_task
from framework.postcommit_tasks.handlers import enqueue_postcommit_task
from osf.models import Guid, GuidMetadataRecord, BaseFileNode, NodeLog
from osf.models.admin_log_entry import (
    update_admin_log,
    FILE_REMOVED,
    FILE_VERSION_REMOVED,
)
from osf.models.files import File, FileVersion, TrashedFile, TrashedFolder
from website.files.exceptions import FileNodeCheckedOutError, FileNodeIsPrimaryFile


class FileSearchView(PermissionRequiredMixin, FormView):
    """ Allows authorized users to search for a specific file by guid.
    """
    template_name = 'files/search.html'
    permission_required = 'osf.view_basefilenode'
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
    permission_required = 'osf.view_basefilenode'
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
        is_trashed = isinstance(file, (TrashedFile, TrashedFolder))
        # Annotate version_id because django templates prohibit accessing attributes that start with underscores
        versions = file.versions.all().order_by('-created').annotate(version_id=F('_id')) if isinstance(file, File) else FileVersion.objects.none()

        selected_version_id = self.request.GET.get('version')
        selected_version = versions.filter(version_id=selected_version_id).first() if selected_version_id else None
        if selected_version is None:
            selected_version = versions.first()

        context.update({
            'guid': guid,
            'node_id': node._id if node else None,
            'node': node,
            'file_metadata': metadata_record,
            'version': selected_version.location.get('version', '') if selected_version else '',
            'versions': versions,
            'selected_version': selected_version,
            'is_trashed': is_trashed,
        })
        return context


class FileDeleteView(FileMixin, View):
    """ Allows authorized users to delete a file or folder (soft delete / trash).
    """
    permission_required = 'osf.delete_basefilenode'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        file = self.get_object()
        if isinstance(file, (TrashedFile, TrashedFolder)):
            messages.error(request, 'This file has already been deleted.')
            return redirect(self.get_success_url())

        node = file.target
        file_path = getattr(file, 'materialized_path', None) or getattr(file, 'path', None) or ''
        guid = self.kwargs['guid']

        try:
            with transaction.atomic():
                file.delete(user=request.user)
                if node is not None and hasattr(node, 'add_log'):
                    params = dict(getattr(node, 'log_params', {}))
                    params.update({
                        'pathType': 'file',
                        'path': file_path,
                    })
                    node.add_log(
                        action=NodeLog.FILE_REMOVED,
                        auth=None,
                        foreign_user=NodeLog.SUPPORT_USER_LABEL,
                        params=params,
                        log_date=timezone.now(),
                        should_hide=False,
                    )
        except FileNodeCheckedOutError:
            messages.error(request, 'This file is checked out and cannot be deleted until it is checked in.')
            return redirect(self.get_success_url())
        except FileNodeIsPrimaryFile:
            messages.error(request, 'This file is the primary file of a preprint and cannot be deleted.')
            return redirect(self.get_success_url())

        update_admin_log(
            user_id=request.user.id,
            object_id=guid,
            object_repr='BaseFileNode',
            message=f'File {guid} deleted by admin.',
            action_flag=FILE_REMOVED,
        )
        messages.success(request, 'File deleted.')
        return redirect(reverse('home'))


class FileVersionDeleteView(FileMixin, View):
    """ Allows authorized users to delete a single version of a file, unlinking
    it from the file and enqueueing a task to purge the underlying storage blob.
    """
    permission_required = 'osf.delete_fileversion'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        file = self.get_object()
        guid = self.kwargs['guid']

        if not isinstance(file, File):
            messages.error(request, 'Only individual files have versions.')
            return redirect(self.get_success_url())

        version_id = self.kwargs.get('version_id')
        version = FileVersion.load(version_id)
        if version is None:
            messages.error(request, 'Version not found.')
            return redirect(self.get_success_url())

        through = version.get_basefilenode_version(file)
        if through is None:
            messages.error(request, 'This version does not belong to this file.')
            return redirect(self.get_success_url())

        if file.versions.count() <= 1:
            messages.error(request, 'Cannot delete the only version of a file. Delete the whole file instead.')
            return redirect(self.get_success_url())

        with transaction.atomic():
            through.delete()

        enqueue_postcommit_task(purge_file_version_task, (version.pk,), {}, celery=True)

        update_admin_log(
            user_id=request.user.id,
            object_id=guid,
            object_repr='FileVersion',
            message=f'Version {version_id} of file {guid} unlinked by admin; GCS purge enqueued.',
            action_flag=FILE_VERSION_REMOVED,
        )
        messages.success(request, 'File version deleted.')
        return redirect(self.get_success_url())
