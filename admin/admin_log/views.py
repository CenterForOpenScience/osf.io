from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView

from osf.models import AdminLogEntry
from osf.models import admin_log_entry as ale

ACTION_LABELS = {
    ale.UNKNOWN: 'Unknown',
    ale.CONFIRM_SPAM: 'Confirm Spam',
    ale.CONFIRM_HAM: 'Confirm Ham',
    ale.UNFLAG_SPAM: 'Unflag Spam',
    ale.NODE_REMOVED: 'Node Removed',
    ale.NODE_RESTORED: 'Node Restored',
    ale.CONTRIBUTOR_REMOVED: 'Contributor Removed',
    ale.NODE_MADE_PRIVATE: 'Node Made Private',
    ale.EMBARGO_UPDATED: 'Embargo Updated',
    ale.USER_REMOVED: 'User Removed',
    ale.USER_RESTORED: 'User Restored',
    ale.USER_2_FACTOR: 'User 2 Factor',
    ale.USER_EMAILED: 'User Emailed',
    ale.USER_GDPR_DELETED: 'User GDPR Deleted',
    ale.USER_SHARE_INDEXING_CHANGED: 'User SHARE Indexing Changed',
    ale.REINDEX_SHARE: 'Reindex SHARE',
    ale.REINDEX_ELASTIC: 'Reindex Elastic',
    ale.APPROVE_WITHDRAWAL: 'Approve Withdrawal',
    ale.REJECT_WITHDRAWAL: 'Reject Withdrawal',
    ale.PREPRINT_REMOVED: 'Preprint Removed',
    ale.PREPRINT_RESTORED: 'Preprint Restored',
    ale.PREPRINT_RECOVERED: 'Preprint Recovered',
    ale.DOI_CREATION_FAILED: 'DOI Creation Failed',
    ale.DOI_UPDATE_FAILED: 'DOI Update Failed',
    ale.MANUAL_ARCHIVE_RESTART: 'Manual Archive Restart',
    ale.FILE_REMOVED: 'File Removed',
    ale.FILE_VERSION_REMOVED: 'File Version Removed',
    ale.REMOVE_GUID: 'Remove Guid',
}


class AdminLogEntryListView(PermissionRequiredMixin, ListView):
    template_name = 'admin_log/list.html'
    context_object_name = 'entries'
    paginate_by = 50
    paginate_orphans = 1
    permission_required = 'osf.view_adminlogentry'
    raise_exception = True

    def get_queryset(self):
        return AdminLogEntry.objects.select_related('user').order_by('-action_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for entry in context['entries']:
            entry.action_label = ACTION_LABELS.get(entry.action_flag, entry.action_flag)
        context['page'] = context['page_obj']
        return context
