from __future__ import unicode_literals

from django.views.generic import UpdateView, DeleteView
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import redirect

from osf.models.preprint_service import PreprintService
from osf.models.admin_log_entry import update_admin_log, REINDEX_SHARE
from website.preprints.tasks import update_preprint_share

from framework.exceptions import PermissionsError
from admin.base.views import GuidFormView, GuidView
from admin.nodes.templatetags.node_extras import reverse_preprint
from admin.preprints.serializers import serialize_preprint
from admin.preprints.forms import ChangeProviderForm


class PreprintFormView(PermissionRequiredMixin, GuidFormView):
    """ Allow authorized admin user to input specific preprint guid.

    Basic form. No admin models.
    """
    template_name = 'preprints/search.html'
    object_type = 'preprint'
    permission_required = 'osf.view_preprintservice'
    raise_exception = True

    @property
    def success_url(self):
        return reverse_preprint(self.guid)


class PreprintView(PermissionRequiredMixin, UpdateView, GuidView):
    """ Allow authorized admin user to view preprints

    View of OSF database. No admin models.
    """
    template_name = 'preprints/preprint.html'
    context_object_name = 'preprintservice'
    permission_required = 'osf.view_preprintservice'
    raise_exception = True
    form_class = ChangeProviderForm

    def get_success_url(self):
        return reverse_lazy('preprints:preprint', kwargs={'guid': self.kwargs.get('guid')})

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('osf.change_preprintservice'):
            raise PermissionsError("This user does not have permission to update this preprint's provider.")
        return super(PreprintView, self).post(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return PreprintService.load(self.kwargs.get('guid'))

    def get_context_data(self, **kwargs):
        preprint = PreprintService.load(self.kwargs.get('guid'))
        # TODO - we shouldn't need this serialized_preprint value -- https://openscience.atlassian.net/browse/OSF-7743
        kwargs['serialized_preprint'] = serialize_preprint(preprint)
        kwargs['change_provider_form'] = ChangeProviderForm(instance=preprint)
        return super(PreprintView, self).get_context_data(**kwargs)


class PreprintReindexShare(PermissionRequiredMixin, DeleteView):
    template_name = 'preprints/reindex_preprint_share.html'
    context_object_name = 'preprintservice'
    object = None
    permission_required = 'osf.view_preprintservice'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('guid', kwargs.get('object')._id)
        return super(PreprintReindexShare, self).get_context_data(**context)

    def get_object(self, queryset=None):
        return PreprintService.load(self.kwargs.get('guid'))

    def delete(self, request, *args, **kwargs):
        preprint = self.get_object()
        update_preprint_share(preprint)
        update_admin_log(
            user_id=self.request.user.id,
            object_id=preprint._id,
            object_repr='Preprint',
            message='Preprint Reindexed (SHARE): {}'.format(preprint._id),
            action_flag=REINDEX_SHARE
        )
        return redirect(reverse_preprint(self.kwargs.get('guid')))
