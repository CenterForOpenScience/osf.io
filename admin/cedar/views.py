from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, UpdateView
from django.urls import reverse

from osf.models.cedar_metadata import CedarMetadataTemplate
from admin.cedar.forms import CedarMetadataTemplateForm

class CedarMetadataTemplateListView(PermissionRequiredMixin, ListView):
    template_name = 'cedar/list.html'
    paginate_by = 10
    paginate_orphans = 1
    context_object_name = 'cedar_metadata_template'
    permission_required = 'osf.view_cedarmetadatatemplate'
    raise_exception = True

    def get_queryset(self):
        return CedarMetadataTemplate.objects.all()

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(queryset)
        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset, page_size
        )
        kwargs.setdefault('cedar_metadata_templates', queryset)
        kwargs.setdefault('page', page)
        return super().get_context_data(**kwargs)

class CedarMetadataTemplateDetailView(PermissionRequiredMixin, UpdateView):
    template_name = 'cedar/detail.html'
    form_class = CedarMetadataTemplateForm
    model = CedarMetadataTemplate
    permission_required = 'osf.change_cedarmetadatatemplate'

    def get_object(self, queryset=None):
        template_id = self.kwargs.get('id')
        return CedarMetadataTemplate.objects.get(id=template_id)

    def get_success_url(self):
        return reverse('cedar_metadata_templates:list')
