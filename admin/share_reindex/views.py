from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse
from django.shortcuts import redirect
from django.views.generic import ListView, View
from osf.models import Guid
from django.db.models import F, Q
from django.contrib.contenttypes.models import ContentType
from osf.models import Registration, Preprint, Node, OSFUser
from urllib.parse import urlencode


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
        resource_type_detail_mapping = {
            'users': 'users:user', 'preprints': 'preprints:preprint', 'registries': 'nodes:node', 'projects': 'nodes:node'
        }

        kwargs.setdefault('resource_detail', resource_type_detail_mapping.get(resource_type))
        resource_type_guid_reindex = {
            'users': 'nodes:reindex-share-node', 'preprints': 'preprints:reindex-share-preprint', 'registries': 'nodes:reindex-share-node', 'projects': 'nodes:reindex-share-node'
        }
        kwargs.setdefault('resource_guid_reindex', resource_type_guid_reindex.get(resource_type))
        status_msg = f'Reindex of {resource_type} started, please check in several minutes.' if self.request.GET.get('status') == 'indexing' else ''
        kwargs.setdefault('share_reindex_message', status_msg)
        # import pydevd_pycharm
        # pydevd_pycharm.settrace('host.docker.internal', port=1234, stdout_to_server=True, stderr_to_server=True)
        return super().get_context_data(**kwargs)


class FailedShareIndexedGuidReindex(PermissionRequiredMixin, View):
    permission_required = 'osf.update_share_reindex'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        # import pydevd_pycharm
        # pydevd_pycharm.settrace('host.docker.internal', port=1234, stdout_to_server=True, stderr_to_server=True)
        # 1. Get the guid from the URL string
        resource_type = self.kwargs.get('resource_type')
        base_url = reverse('share_reindex:list')
        query_string = urlencode({'type': resource_type, 'status': 'indexing'})
        return redirect(f"{base_url}?{query_string}")
