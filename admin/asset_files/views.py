from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.urlresolvers import reverse_lazy
from django.db.models import Case, CharField, Value, When
from django.forms.models import model_to_dict
from django.views.generic import ListView, DetailView, View, CreateView, DeleteView, UpdateView

from admin.asset_files.forms import ProviderAssetFileForm
from osf.models.provider import AbstractProvider
from osf.models.storage import ProviderAssetFile

class ProviderAssetFileList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'asset_files/list.html'
    ordering = 'name'
    permission_required = 'osf.view_asset_files'
    raise_exception = True
    model = ProviderAssetFile

    def get_queryset(self):
        filtered_provider_id = self.request.GET.get('provider_id', None)
        qs = ProviderAssetFile.objects.all().order_by(self.ordering)
        if filtered_provider_id and AbstractProvider.objects.filter(_id=filtered_provider_id).exists():
            qs = qs.filter(providers___id=filtered_provider_id)
        return qs

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        rv = {
            'asset_files': query_set,
            'page': page,
            'filterable_provider_ids': dict({'': '---'}, **{_id: ' '.join([type_, name]) for _id, name, type_ in AbstractProvider.objects.annotate(
                type_=Case(
                    When(type='osf.preprintprovider', then=Value('[preprint]')),
                    When(type='osf.collectionprovider', then=Value('[collection]')),
                    default=Value('[unknown]'),
                    output_field=CharField()
                )
            ).values_list('_id', 'name', 'type_')}),
        }
        return rv

class AssetFileMixin(object):
    def get_object(self, queryset=None):
        return ProviderAssetFile.objects.get(id=self.kwargs.get('asset_id'))

class ProviderAssetFileDisplay(AssetFileMixin, PermissionRequiredMixin, DetailView):
    permission_required = 'osf.view_asset_files'
    template_name = 'asset_files/detail.html'
    form_class = ProviderAssetFileForm
    raise_exception = True
    model = ProviderAssetFile

    def get_context_data(self, **kwargs):
        instance = self.get_object()
        kwargs['form'] = self.form_class(model_to_dict(instance), instance=instance)
        # Assumption: only css files will not be images. This may be incorrect in the future, but currently is not.
        kwargs['embed_file'] = instance.file and not instance.file.url.endswith('.css')
        return kwargs

class ProviderAssetFileChangeForm(AssetFileMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'osf.change_asset_files'
    raise_exception = True
    model = ProviderAssetFile
    form_class = ProviderAssetFileForm

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('asset_files:detail', kwargs={'asset_id': self.kwargs.get('asset_id')})

class ProviderAssetFileDelete(AssetFileMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'osf.delete_asset_files'
    raise_exception = True
    template_name = 'asset_files/confirm_delete.html'
    success_url = reverse_lazy('asset_files:list')


class ProviderAssetFileDetail(PermissionRequiredMixin, View):
    permission_required = 'osf.view_asset_files'
    raise_exception = True
    form_class = ProviderAssetFileForm

    def get(self, request, *args, **kwargs):
        view = ProviderAssetFileDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = ProviderAssetFileChangeForm.as_view()
        return view(request, *args, **kwargs)

class ProviderAssetFileCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'osf.change_asset_files'
    raise_exception = True
    template_name = 'asset_files/create.html'
    success_url = reverse_lazy('asset_files:list')
    model = ProviderAssetFile
    form_class = ProviderAssetFileForm
