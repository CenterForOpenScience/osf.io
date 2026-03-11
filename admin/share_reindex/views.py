from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView
from osf.models import Guid
from django.db.models import F, Q

from django.contrib.contenttypes.models import ContentType
from osf.models import Registration, Preprint, Node, OSFUser


class FailedShareIndexedGuidList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'share_reindex/list.html'
    permission_required = 'osf.update_share_reindex'
    raise_exception = True
    model = Guid

    def get_queryset(self):
        resource_type = self.request.GET.get('type', 'projects')
        resource_mapper = {
            'projects': (Node, Q(is_public=True)),
            'preprints': (Preprint, Q(is_public=True)),
            'registries': (Registration, Q(is_public=True)),
            'users': (OSFUser, Q(is_active=True))
        }

        resource_model, query = resource_mapper.get(resource_type)

        node_type = ContentType.objects.get_for_model(resource_model)
        public_node_ids = resource_model.objects.filter(query).values_list('id', flat=True)
        # import pydevd_pycharm
        # pydevd_pycharm.settrace('host.docker.internal', port=1234, stdout_to_server=True, stderr_to_server=True)
        return Guid.objects.filter(
            Q(has_been_indexed=False) | Q(has_been_indexed=None),
            content_type=node_type,
            object_id__in=public_node_ids
        ).annotate(custom_id=F('_id'))

    def get_context_data(self, **kwargs):
        # import pydevd_pycharm
        # pydevd_pycharm.settrace('host.docker.internal', port=1234, stdout_to_server=True, stderr_to_server=True)
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('guids', query_set)
        kwargs.setdefault('page', page)
        resource_type = self.request.GET.get('type', 'projects')
        kwargs.setdefault('selected_resource_type', resource_type)
        return super().get_context_data(**kwargs)
