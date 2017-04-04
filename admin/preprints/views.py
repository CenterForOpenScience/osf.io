from __future__ import unicode_literals

from django.views.generic import UpdateView
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.mixins import PermissionRequiredMixin


from website.preprints.model import PreprintService
from framework.exceptions import PermissionsError
from admin.base.views import GuidFormView, GuidView
from admin.nodes.templatetags.node_extras import reverse_preprint
from admin.preprints.serializers import serialize_preprint, serialize_subjects
from admin.preprints.forms import ChangeProviderForm


class PreprintFormView(PermissionRequiredMixin, GuidFormView):
    """ Allow authorized admin user to input specific preprint guid.

    Basic form. No admin models.
    """
    template_name = 'preprints/search.html'
    object_type = 'preprint'
    permission_required = 'osf.view_node'
    raise_exception = True

    @property
    def success_url(self):
        return reverse_preprint(self.guid)


class PreprintView(PermissionRequiredMixin, UpdateView, GuidView):
    """ Allow authorized admin user to view preprints

    View of OSF database. No admin models.
    """
    template_name = 'preprints/preprint.html'
    context_object_name = 'preprint'
    permission_required = 'osf.view_preprintservice'
    raise_exception = True
    form_class = ChangeProviderForm

    def get_success_url(self):
        return reverse_lazy('preprints:preprint', kwargs={'guid': self.kwargs.get('guid')})

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('osf.change_preprintservice'):
            raise PermissionsError("This user does not have permission to update this preprint's provider.")

    def get_object(self, queryset=None):
        return PreprintService.load(self.kwargs.get('guid'))

    def get_context_data(self, **kwargs):
        preprint = PreprintService.load(self.kwargs.get('guid'))
        # TODO - we shouldn't need this serialized_preprint value -- https://openscience.atlassian.net/browse/OSF-7743
        kwargs['serialized_preprint'] = serialize_preprint(preprint)
        kwargs['change_provider_form'] = ChangeProviderForm(instance=preprint)
        kwargs['subjects'] = serialize_subjects(preprint.subjects)
        return super(PreprintView, self).get_context_data(**kwargs)
