import json

from django.http import HttpResponse
from django.core import serializers
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import View, CreateView, ListView, DetailView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.forms.models import model_to_dict

from admin.collection_providers.forms import CollectionProviderForm
from admin.base import settings
from admin.base.forms import ImportFileForm
from osf.models import Collection, CollectionProvider, NodeLicense


class CreateCollectionProvider(PermissionRequiredMixin, CreateView):
    raise_exception = True
    permission_required = 'osf.change_collectionprovider'
    template_name = 'collection_providers/create.html'
    model = CollectionProvider
    form_class = CollectionProviderForm
    success_url = reverse_lazy('collection_providers:list')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object._creator = self.request.user
        self.object.save()
        for item in form.cleaned_data['collected_type_choices']['added']:
            self.object.primary_collection.collected_type_choices.append(item)
        for item in form.cleaned_data['status_choices']['added']:
            self.object.primary_collection.status_choices.append(item)
        for item in form.cleaned_data['volume_choices']['added']:
            self.object.primary_collection.volume_choices.append(item)
        for item in form.cleaned_data['issue_choices']['added']:
            self.object.primary_collection.issue_choices.append(item)
        for item in form.cleaned_data['program_area_choices']['added']:
            self.object.primary_collection.program_area_choices.append(item)
        self.object.primary_collection.save()
        return super(CreateCollectionProvider, self).form_valid(form)

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        kwargs['tinymce_apikey'] = settings.TINYMCE_APIKEY
        return super(CreateCollectionProvider, self).get_context_data(*args, **kwargs)


class CollectionProviderList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'collection_providers/list.html'
    ordering = 'name'
    permission_required = 'osf.change_collectionprovider'
    raise_exception = True
    model = CollectionProvider

    def get_queryset(self):
        return CollectionProvider.objects.all().order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'collection_providers': query_set,
            'page': page,
        }


class CollectionProviderDetail(PermissionRequiredMixin, View):
    permission_required = 'osf.change_collectionprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        view = CollectionProviderDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = CollectionProviderChangeForm.as_view()
        return view(request, *args, **kwargs)


class CollectionProviderDisplay(PermissionRequiredMixin, DetailView):
    model = CollectionProvider
    template_name = 'collection_providers/detail.html'
    permission_required = 'osf.view_collectionprovider'
    raise_exception = True

    def get_object(self, queryset=None):
        return CollectionProvider.objects.get(id=self.kwargs.get('collection_provider_id'))

    def get_context_data(self, *args, **kwargs):
        collection_provider = self.get_object()
        collection_provider_attributes = model_to_dict(collection_provider)
        collection_provider_attributes['default_license'] = collection_provider.default_license.name if collection_provider.default_license else None
        kwargs['collection_provider'] = collection_provider_attributes
        kwargs['import_form'] = ImportFileForm()

        # compile html list of licenses_acceptable so we can render them as a list
        licenses_acceptable = list(collection_provider.licenses_acceptable.values_list('name', flat=True))
        licenses_html = '<ul>'
        for license in licenses_acceptable:
            licenses_html += '<li>{}</li>'.format(license)
        licenses_html += '</ul>'
        collection_provider_attributes['licenses_acceptable'] = licenses_html

        # compile html list of collected_type_choices
        collected_type_choices_html = '<ul>'
        for choice in collection_provider.primary_collection.collected_type_choices:
            collected_type_choices_html += u'<li>{}</li>'.format(choice)
        collected_type_choices_html += '</ul>'
        kwargs['collected_type_choices'] = collected_type_choices_html

        # compile html list of status_choices
        status_choices_html = '<ul>'
        for choice in collection_provider.primary_collection.status_choices:
            status_choices_html += u'<li>{}</li>'.format(choice)
        status_choices_html += '</ul>'
        kwargs['status_choices'] = status_choices_html

        # compile html list of volume_choices
        volume_choices_html = '<ul>'
        for choice in collection_provider.primary_collection.volume_choices:
            volume_choices_html += u'<li>{}</li>'.format(choice)
        volume_choices_html += '</ul>'
        kwargs['volume_choices'] = volume_choices_html

        # compile html list of issue_choices
        issue_choices_html = '<ul>'
        for choice in collection_provider.primary_collection.issue_choices:
            issue_choices_html += u'<li>{}</li>'.format(choice)
        issue_choices_html += '</ul>'
        kwargs['issue_choices'] = issue_choices_html

        # compile html list of program_area_choices
        program_area_choices_html = '<ul>'
        for choice in collection_provider.primary_collection.program_area_choices:
            program_area_choices_html += u'<li>{}</li>'.format(choice)
        program_area_choices_html += '</ul>'
        kwargs['program_area_choices'] = program_area_choices_html

        # get a dict of model fields so that we can set the initial value for the update form
        fields = model_to_dict(collection_provider)
        fields['collected_type_choices'] = json.dumps(collection_provider.primary_collection.collected_type_choices)
        fields['status_choices'] = json.dumps(collection_provider.primary_collection.status_choices)
        fields['volume_choices'] = json.dumps(collection_provider.primary_collection.volume_choices)
        fields['issue_choices'] = json.dumps(collection_provider.primary_collection.issue_choices)
        fields['program_area_choices'] = json.dumps(collection_provider.primary_collection.program_area_choices)
        kwargs['form'] = CollectionProviderForm(initial=fields)

        # set api key for tinymce
        kwargs['tinymce_apikey'] = settings.TINYMCE_APIKEY

        return kwargs


class CollectionProviderChangeForm(PermissionRequiredMixin, UpdateView):
    permission_required = 'osf.change_collectionprovider'
    raise_exception = True
    model = CollectionProvider
    form_class = CollectionProviderForm

    def form_valid(self, form):
        self.object.primary_collection.collected_type_choices.extend(form.cleaned_data['collected_type_choices']['added'])
        for item in form.cleaned_data['collected_type_choices']['removed']:
            self.object.primary_collection.collected_type_choices.remove(item)

        self.object.primary_collection.status_choices.extend(form.cleaned_data['status_choices']['added'])
        for item in form.cleaned_data['status_choices']['removed']:
            self.object.primary_collection.status_choices.remove(item)

        self.object.primary_collection.issue_choices.extend(form.cleaned_data['issue_choices']['added'])
        for item in form.cleaned_data['issue_choices']['removed']:
            self.object.primary_collection.issue_choices.remove(item)

        self.object.primary_collection.volume_choices.extend(form.cleaned_data['volume_choices']['added'])
        for item in form.cleaned_data['volume_choices']['removed']:
            self.object.primary_collection.volume_choices.remove(item)

        self.object.primary_collection.program_area_choices.extend(form.cleaned_data['program_area_choices']['added'])
        for item in form.cleaned_data['program_area_choices']['removed']:
            self.object.primary_collection.program_area_choices.remove(item)

        self.object.primary_collection.save()
        return super(CollectionProviderChangeForm, self).form_valid(form)

    def form_invalid(self, form):
        super(CollectionProviderChangeForm, self).form_invalid(form)
        err_message = ''
        for item in form.errors.values():
            err_message = err_message + item + '\n'
        return HttpResponse(err_message, status=409)

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        return super(CollectionProviderChangeForm, self).get_context_data(*args, **kwargs)

    def get_object(self, queryset=None):
        provider_id = self.kwargs.get('collection_provider_id')
        return CollectionProvider.objects.get(id=provider_id)

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('collection_providers:detail',
                            kwargs={'collection_provider_id': self.kwargs.get('collection_provider_id')})


class DeleteCollectionProvider(PermissionRequiredMixin, DeleteView):
    permission_required = 'osf.delete_collectionprovider'
    raise_exception = True
    template_name = 'collection_providers/confirm_delete.html'
    success_url = reverse_lazy('collection_providers:list')

    def delete(self, request, *args, **kwargs):
        provider = CollectionProvider.objects.get(id=self.kwargs['collection_provider_id'])
        if provider.primary_collection.collectionsubmission_set.count() > 0:
            return redirect('collection_providers:cannot_delete', collection_provider_id=provider.pk)
        return super(DeleteCollectionProvider, self).delete(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        provider = CollectionProvider.objects.get(id=self.kwargs['collection_provider_id'])
        if provider.primary_collection.collectionsubmission_set.count() > 0:
            return redirect('collection_providers:cannot_delete', collection_provider_id=provider.pk)
        return super(DeleteCollectionProvider, self).get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return CollectionProvider.objects.get(id=self.kwargs['collection_provider_id'])


class CannotDeleteProvider(TemplateView):
    template_name = 'collection_providers/cannot_delete.html'

    def get_context_data(self, **kwargs):
        context = super(CannotDeleteProvider, self).get_context_data(**kwargs)
        context['provider'] = CollectionProvider.objects.get(id=self.kwargs['collection_provider_id'])
        return context


class ExportColectionProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_collectionprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        collection_provider = CollectionProvider.objects.get(id=self.kwargs['collection_provider_id'])
        data = serializers.serialize('json', [collection_provider])
        cleaned_data = json.loads(data)[0]
        cleaned_fields = cleaned_data['fields']
        cleaned_fields['licenses_acceptable'] = [node_license.license_id for node_license in collection_provider.licenses_acceptable.all()]
        cleaned_fields['default_license'] = collection_provider.default_license.license_id if collection_provider.default_license else ''
        cleaned_fields['primary_collection'] = self.serialize_primary_collection(cleaned_fields['primary_collection'])
        cleaned_data['fields'] = cleaned_fields
        filename = '{}_export.json'.format(collection_provider.name)
        response = HttpResponse(json.dumps(cleaned_data), content_type='text/json')
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response

    def serialize_primary_collection(self, primary_collection):
        primary_collection = Collection.objects.get(id=primary_collection)
        data = serializers.serialize('json', [primary_collection])
        cleaned_data = json.loads(data)[0]
        return cleaned_data


class ImportCollectionProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_collectionprovider'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_str = self.parse_file(request.FILES['file'])
            file_json = json.loads(file_str)
            cleaned_result = file_json['fields']
            collection_provider = self.create_or_update_provider(cleaned_result)
            return redirect('collection_providers:detail', collection_provider_id=collection_provider.id)

    def parse_file(self, f):
        parsed_file = ''
        for chunk in f.chunks():
            parsed_file += chunk.decode('utf-8')
        return parsed_file

    def get_page_provider(self):
        page_provider_id = self.kwargs.get('collection_provider_id', '')
        if page_provider_id:
            return CollectionProvider.objects.get(id=page_provider_id)

    def create_or_update_provider(self, provider_data):
        provider = self.get_page_provider()
        licenses = [NodeLicense.objects.get(license_id=license_id) for license_id in provider_data.pop('licenses_acceptable', [])]
        default_license = provider_data.pop('default_license', False)
        primary_collection = provider_data.pop('primary_collection', None)
        provider_data.pop('additional_providers')

        if provider:
            for key, val in provider_data.items():
                setattr(provider, key, val)
            provider.save()
        else:
            provider = CollectionProvider(**provider_data)
            provider._creator = self.request.user
            provider.save()

        if primary_collection:
            provider.primary_collection.collected_type_choices = primary_collection['fields']['collected_type_choices']
            provider.primary_collection.status_choices = primary_collection['fields']['status_choices']
            provider.primary_collection.issue_choices = primary_collection['fields']['issue_choices']
            provider.primary_collection.volume_choices = primary_collection['fields']['volume_choices']
            provider.primary_collection.program_area_choices = primary_collection['fields']['program_area_choices']
            provider.primary_collection.save()
        if licenses:
            provider.licenses_acceptable = licenses
        if default_license:
            provider.default_license = NodeLicense.objects.get(license_id=default_license)
        return provider
