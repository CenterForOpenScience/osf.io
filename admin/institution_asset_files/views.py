from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse_lazy
from django.forms.models import model_to_dict
from django.views.generic import ListView, DetailView, View, CreateView, DeleteView, UpdateView

from admin.institution_asset_files.forms import InstitutionAssetFileForm
from osf.models.storage import InstitutionAssetFile
from osf.models.institution import Institution

class InstitutionAssetFileList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'osf/assetfile_list.html'
    ordering = 'name'
    permission_required = 'osf.view_institutionassetfile'
    raise_exception = True
    model = InstitutionAssetFile

    def get_queryset(self):
        filtered_institution_id = self.request.GET.get('institution_id', None)
        qs = InstitutionAssetFile.objects.all().order_by(self.ordering)
        if filtered_institution_id and Institution.objects.filter(id=filtered_institution_id).exists():
            qs = qs.filter(institutions__id=filtered_institution_id)
        return qs

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        rv = {
            'on_institution_route': True,
            'asset_files': query_set,
            'page': page,
            'filterable_target_ids': dict({'': '---'}, **{str(id): ' '.join([name]) for id, name in Institution.objects.all().values_list('id', 'name')}),
        }
        return rv

class AssetFileMixin:
    def get_object(self, queryset=None):
        return InstitutionAssetFile.objects.get(id=self.kwargs.get('asset_id'))

class InstitutionAssetFileDisplay(AssetFileMixin, PermissionRequiredMixin, DetailView):
    permission_required = 'osf.view_institutionassetfile'
    template_name = 'osf/assetfile_form.html'
    form_class = InstitutionAssetFileForm
    raise_exception = True
    model = InstitutionAssetFile

    def get_context_data(self, **kwargs):
        instance = self.get_object()
        kwargs['form'] = self.form_class(model_to_dict(instance), instance=instance)
        # Assumption: only css files will not be images. This may be incorrect in the future, but currently is not.
        kwargs['embed_file'] = instance.file and not instance.file.url.endswith('.css')
        kwargs['on_institution_route'] = True
        return kwargs

class InstitutionAssetFileChangeForm(AssetFileMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'osf.change_institutionassetfile'
    raise_exception = True
    model = InstitutionAssetFile
    form_class = InstitutionAssetFileForm

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('institution_asset_files:detail', kwargs={'asset_id': self.kwargs.get('asset_id')})

class InstitutionAssetFileDelete(AssetFileMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'osf.delete_institutionassetfile'
    raise_exception = True
    template_name = 'osf/assetfile_confirm_delete.html'
    success_url = reverse_lazy('institution_asset_files:list')


class InstitutionAssetFileDetail(PermissionRequiredMixin, View):
    permission_required = 'osf.view_institutionassetfile'
    raise_exception = True
    form_class = InstitutionAssetFileForm

    def get(self, request, *args, **kwargs):
        view = InstitutionAssetFileDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = InstitutionAssetFileChangeForm.as_view()
        return view(request, *args, **kwargs)

class InstitutionAssetFileCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'osf.change_institutionassetfile'
    raise_exception = True
    template_name = 'osf/assetfile_create.html'
    success_url = reverse_lazy('institution_asset_files:list')
    model = InstitutionAssetFile
    form_class = InstitutionAssetFileForm
