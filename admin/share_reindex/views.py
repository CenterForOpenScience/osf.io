from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse
from django.shortcuts import redirect
from django.views.generic import ListView, View
from osf.models import Guid
from django.db.models import F
from urllib.parse import urlencode
from api.share.utils import get_not_indexed_guids_for_resource_with_no_indexed_guid, task__reindex_resource_into_share

class FailedShareIndexedGuidList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'share_reindex/list.html'
    permission_required = 'osf.update_share_reindex'
    raise_exception = True
    model = Guid

    def get_queryset(self):
        resource_type = self.request.GET.get('type', 'projects')
        # use custom_id because _id fails to render in django template
        return get_not_indexed_guids_for_resource_with_no_indexed_guid(resource_type).annotate(custom_id=F('_id'))

    def get_context_data(self, **kwargs):
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
            'users': 'users:reindex-share-user', 'preprints': 'preprints:reindex-share-preprint', 'registries': 'nodes:reindex-share-node', 'projects': 'nodes:reindex-share-node'
        }
        kwargs.setdefault('resource_guid_reindex', resource_type_guid_reindex.get(resource_type))
        status_msg = f'Reindex of {resource_type} started, please check in several minutes.' if self.request.GET.get('status') == 'indexing' else ''
        kwargs.setdefault('share_reindex_message', status_msg)
        return super().get_context_data(**kwargs)


class FailedShareIndexedGuidReindex(PermissionRequiredMixin, View):
    permission_required = 'osf.update_share_reindex'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        resource_type = self.kwargs.get('resource_type')
        # reindex 100_000 guids in background task for specific resource_type and resource is public
        task__reindex_resource_into_share.delay(resource_type, 100_000)
        base_url = reverse('share_reindex:list')
        query_string = urlencode({'type': resource_type, 'status': 'indexing'})
        return redirect(f"{base_url}?{query_string}")
