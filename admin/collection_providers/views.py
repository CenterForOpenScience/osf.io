import json

from django.core.urlresolvers import reverse_lazy
from django.views.generic import View, CreateView, ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.forms.models import model_to_dict

from admin.collection_providers.forms import CollectionProviderForm
from admin.base import settings
from osf.models import CollectionProvider


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
        for item in json.loads(form.cleaned_data['collected_type_choices']):
            self.object.primary_collection.collected_type_choices.append(item)
        for item in json.loads(form.cleaned_data['status_choices']):
            self.object.primary_collection.status_choices.append(item)
        self.object.primary_collection.save()
        return super(CreateCollectionProvider, self).form_valid(form)

    def get_context_data(self, *args, **kwargs):
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
            collected_type_choices_html += '<li>{}</li>'.format(choice)
        collected_type_choices_html += '</ul>'
        kwargs['collected_type_choices'] = collected_type_choices_html

        # compile html list of status_choices
        status_choices_html = '<ul>'
        for choice in collection_provider.primary_collection.status_choices:
            status_choices_html += '<li>{}</li>'.format(choice)
        status_choices_html += '</ul>'
        kwargs['status_choices'] = status_choices_html

        # get a dict of model fields so that we can set the initial value for the update form
        fields = model_to_dict(collection_provider)
        fields['collected_type_choices'] = json.dumps(collection_provider.primary_collection.collected_type_choices)
        fields['status_choices'] = json.dumps(collection_provider.primary_collection.status_choices)
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
        self.object.primary_collection.collected_type_choices = json.loads(form.cleaned_data['collected_type_choices'])
        self.object.primary_collection.status_choices = json.loads(form.cleaned_data['status_choices'])
        self.object.primary_collection.save()
        return super(CollectionProviderChangeForm, self).form_valid(form)


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

    def get_object(self, queryset=None):
        return CollectionProvider.objects.get(id=self.kwargs['collection_provider_id'])
