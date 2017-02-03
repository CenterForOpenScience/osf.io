from __future__ import unicode_literals

from website.preprints.model import PreprintService
from admin.base.views import GuidFormView, GuidView
from django.contrib.auth.mixins import PermissionRequiredMixin

from admin.nodes.templatetags.node_extras import reverse_preprint
from admin.preprints.serializers import serialize_preprint


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


class PreprintView(PermissionRequiredMixin, GuidView):
    """ Allow authorized admin user to view preprints

    View of OSF database. No admin models.
    """
    template_name = 'preprints/preprint.html'
    context_object_name = 'preprint'
    permission_required = 'osf.view_node'
    raise_exception = True

    def get_object(self, queryset=None):
        return serialize_preprint(PreprintService.load(self.kwargs.get('guid')))
