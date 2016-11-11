from __future__ import unicode_literals

from website.preprints.model import PreprintService
from admin.base.views import GuidFormView, GuidView
from admin.base.utils import OSFAdmin

from admin.nodes.templatetags.node_extras import reverse_preprint
from admin.preprints.serializers import serialize_preprint
from website.project.spam.model import SpamStatus


class PreprintFormView(OSFAdmin, GuidFormView):
    """ Allow authorized admin user to input specific preprint guid.

    Basic form. No admin models.
    """
    template_name = 'preprints/search.html'
    object_type = 'preprint'

    @property
    def success_url(self):
        return reverse_preprint(self.guid)


class PreprintView(OSFAdmin, GuidView):
    """ Allow authorized admin user to view preprints

    View of OSF database. No admin models.
    """
    template_name = 'preprints/preprint.html'
    context_object_name = 'preprint'

    def get_object(self, queryset=None):
        return serialize_preprint(PreprintService.load(self.kwargs.get('guid')))
