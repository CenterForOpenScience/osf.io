import json

from django.http import HttpResponse
from django.core import serializers
from django.core.management import call_command
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import View, CreateView, ListView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.forms.models import model_to_dict
from django.http import JsonResponse

from admin.registration_providers.forms import RegistrationProviderForm, RegistrationProviderCustomTaxonomyForm
from admin.base import settings
from admin.base.forms import ImportFileForm
from osf.models import RegistrationProvider, NodeLicense


class CreateRegistrationProvider(PermissionRequiredMixin, CreateView):
    raise_exception = True
    permission_required = 'osf.change_registrationprovider'
    template_name = 'registration_providers/create.html'
    model = RegistrationProvider
    form_class = RegistrationProviderForm
    success_url = reverse_lazy('registration_providers:list')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object._creator = self.request.user
        self.object.save()
        return super(CreateRegistrationProvider, self).form_valid(form)

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        kwargs['show_taxonomies'] = True
        kwargs['tinymce_apikey'] = settings.TINYMCE_APIKEY
        return super(CreateRegistrationProvider, self).get_context_data(*args, **kwargs)


class RegistrationProviderList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'registration_providers/list.html'
    ordering = 'name'
    permission_required = 'osf.view_registrationprovider'
    raise_exception = True
    model = RegistrationProvider

    def get_queryset(self):
        return RegistrationProvider.objects.all().order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'registration_providers': query_set,
            'page': page,
        }


class RegistrationProviderDetail(PermissionRequiredMixin, View):
    permission_required = 'osf.change_registrationprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        view = RegistrationProviderDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = RegistrationProviderChangeForm.as_view()
        return view(request, *args, **kwargs)


class RegistrationProviderDisplay(PermissionRequiredMixin, DetailView):
    model = RegistrationProvider
    template_name = 'registration_providers/detail.html'
    permission_required = 'osf.view_registrationprovider'
    raise_exception = True

    def get_object(self, queryset=None):
        return RegistrationProvider.objects.get(id=self.kwargs.get('registration_provider_id'))

    def get_context_data(self, *args, **kwargs):
        registration_provider = self.get_object()
        registration_provider_attributes = model_to_dict(registration_provider)
        registration_provider_attributes['default_license'] = registration_provider.default_license.name if registration_provider.default_license else None

        # compile html list of licenses_acceptable so we can render them as a list
        licenses_acceptable = list(registration_provider.licenses_acceptable.values_list('name', flat=True))
        licenses_html = '<ul>'
        for license in licenses_acceptable:
            licenses_html += '<li>{}</li>'.format(license)
        licenses_html += '</ul>'
        registration_provider_attributes['licenses_acceptable'] = licenses_html

        # compile html list of subjects
        subject_ids = registration_provider.all_subjects.values_list('id', flat=True)
        kwargs['registration_provider'] = registration_provider_attributes
        kwargs['subject_ids'] = list(subject_ids)

        subject_html = '<ul class="subjects-list">'
        for parent in registration_provider.top_level_subjects:
            if parent.id in subject_ids:
                mapped_text = ''
                if parent.bepress_subject and parent.text != parent.bepress_subject.text:
                    mapped_text = ' (mapped from {})'.format(parent.bepress_subject.text)
                hash_id = abs(hash(parent.text))
                subject_html = subject_html + '<li data-id={}>{}'.format(hash_id, parent.text) + mapped_text + '</li>'
                child_html = '<ul class="three-cols" data-id={}>'.format(hash_id)
                for child in parent.children.all():
                    grandchild_html = ''
                    if child.id in subject_ids:
                        child_mapped_text = ''
                        if child.bepress_subject and child.text != child.bepress_subject.text:
                            child_mapped_text = ' (mapped from {})'.format(child.bepress_subject.text)
                        child_html = child_html + '<li>{}'.format(child.text) + child_mapped_text + '</li>'
                        grandchild_html = '<ul>'
                        for grandchild in child.children.all():
                            if grandchild.id in subject_ids:
                                grandchild_mapped_text = ''
                                if grandchild.bepress_subject and grandchild.text != grandchild.bepress_subject.text:
                                    grandchild_mapped_text = ' (mapped from {})'.format(grandchild.bepress_subject.text)
                                grandchild_html = grandchild_html + '<li>{}'.format(grandchild.text) + grandchild_mapped_text + '</li>'
                        grandchild_html += '</ul>'
                    child_html += grandchild_html

                child_html += '</ul>'
                subject_html += child_html

        subject_html += '</ul>'
        registration_provider_attributes['subjects'] = subject_html

        fields = model_to_dict(registration_provider)
        kwargs['show_taxonomies'] = False if registration_provider.subjects.exists() else True
        kwargs['form'] = RegistrationProviderForm(initial=fields)
        kwargs['import_form'] = ImportFileForm()
        kwargs['taxonomy_form'] = RegistrationProviderCustomTaxonomyForm()

        # set api key for tinymce
        kwargs['tinymce_apikey'] = settings.TINYMCE_APIKEY

        return kwargs


class RegistrationProviderChangeForm(PermissionRequiredMixin, UpdateView):
    permission_required = 'osf.change_registrationprovider'
    raise_exception = True
    model = RegistrationProvider
    form_class = RegistrationProviderForm

    def form_invalid(self, form):
        super(RegistrationProviderChangeForm, self).form_invalid(form)
        err_message = ''
        for item in form.errors.values():
            err_message = err_message + item + '\n'
        return HttpResponse(err_message, status=409)

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        return super(RegistrationProviderChangeForm, self).get_context_data(*args, **kwargs)

    def get_object(self, queryset=None):
        provider_id = self.kwargs.get('registration_provider_id')
        return RegistrationProvider.objects.get(id=provider_id)

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('registration_providers:detail',
                            kwargs={'registration_provider_id': self.kwargs.get('registration_provider_id')})


class DeleteRegistrationProvider(PermissionRequiredMixin, DeleteView):
    permission_required = 'osf.delete_registrationprovider'
    raise_exception = True
    template_name = 'registration_providers/confirm_delete.html'
    success_url = reverse_lazy('registration_providers:list')

    def get_object(self, queryset=None):
        return RegistrationProvider.objects.get(id=self.kwargs['registration_provider_id'])

    def get_context_data(self, *args, **kwargs):
        registration_provider = self.get_object()
        kwargs['provider_name'] = registration_provider.name
        kwargs['has_collected_submissions'] = registration_provider.primary_collection.collectionsubmission_set.exists()
        kwargs['collected_submissions_count'] = registration_provider.primary_collection.collectionsubmission_set.count()
        kwargs['provider_id'] = registration_provider.id
        return super(DeleteRegistrationProvider, self).get_context_data(*args, **kwargs)

class ExportRegistrationProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_registrationprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        registration_provider = RegistrationProvider.objects.get(id=self.kwargs['registration_provider_id'])
        data = serializers.serialize('json', [registration_provider])
        cleaned_data = json.loads(data)[0]
        cleaned_fields = cleaned_data['fields']
        cleaned_fields['licenses_acceptable'] = [node_license.license_id for node_license in registration_provider.licenses_acceptable.all()]
        cleaned_fields['default_license'] = registration_provider.default_license.license_id if registration_provider.default_license else ''
        cleaned_fields['subjects'] = self.serialize_subjects(registration_provider)
        cleaned_data['fields'] = cleaned_fields
        filename = '{}_export.json'.format(registration_provider.name)
        response = HttpResponse(json.dumps(cleaned_data), content_type='text/json')
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response

    def serialize_subjects(self, provider):
        if provider._id != 'osf' and provider.subjects.count():
            result = {}
            result['include'] = []
            result['exclude'] = []
            result['custom'] = {
                subject.text: {
                    'parent': subject.parent.text if subject.parent else '',
                    'bepress': subject.bepress_subject.text
                }
                for subject in provider.subjects.all()
            }
            return result


class ImportRegistrationProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_registrationprovider'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_str = self.parse_file(request.FILES['file'])
            file_json = json.loads(file_str)
            cleaned_result = file_json['fields']
            registration_provider = self.create_or_update_provider(cleaned_result)
            return redirect('registration_providers:detail', registration_provider_id=registration_provider.id)

    def parse_file(self, f):
        parsed_file = ''
        for chunk in f.chunks():
            parsed_file += chunk.decode('utf-8')
        return parsed_file

    def get_page_provider(self):
        page_provider_id = self.kwargs.get('registration_provider_id', '')
        if page_provider_id:
            return RegistrationProvider.objects.get(id=page_provider_id)

    def add_subjects(self, provider, subject_data):
        call_command('populate_custom_taxonomies', '--provider', provider._id, '--data', json.dumps(subject_data), '--type', 'osf.registrationprovider')

    def create_or_update_provider(self, provider_data):
        provider = self.get_page_provider()
        licenses = [NodeLicense.objects.get(license_id=license_id) for license_id in provider_data.pop('licenses_acceptable', [])]
        default_license = provider_data.pop('default_license', False)
        subject_data = provider_data.pop('subjects', False)
        provider_data.pop('additional_providers')

        if provider:
            for key, val in provider_data.iteritems():
                setattr(provider, key, val)
            provider.save()
        else:
            provider = RegistrationProvider(**provider_data)
            provider._creator = self.request.user
            provider.save()

        if licenses:
            provider.licenses_acceptable = licenses
        if default_license:
            provider.default_license = NodeLicense.objects.get(license_id=default_license)

        # Only adds the JSON taxonomy if there is no existing taxonomy data
        if subject_data and not provider.subjects.count():
            self.add_subjects(provider, subject_data)
        return provider


class ProcessCustomTaxonomy(PermissionRequiredMixin, View):

    permission_required = 'osf.change_registrationprovider'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        # Import here to avoid test DB access errors when importing registration provider views
        from osf.management.commands.populate_custom_taxonomies import validate_input, migrate

        provider_form = RegistrationProviderCustomTaxonomyForm(request.POST)
        if provider_form.is_valid():
            provider = RegistrationProvider.objects.get(id=provider_form.cleaned_data['provider_id'])
            try:
                taxonomy_json = json.loads(provider_form.cleaned_data['custom_taxonomy_json'])
                if request.is_ajax():
                    # An ajax request is for validation only, so run that validation!
                    try:
                        response_data = validate_input(
                            custom_provider=provider,
                            data=taxonomy_json,
                            provider_type='osf.registrationprovider',
                            add_missing=provider_form.cleaned_data['add_missing'])

                        if response_data:
                            added_subjects = [subject.text for subject in response_data]
                            response_data = {'message': 'Custom taxonomy validated with added subjects: {}'.format(added_subjects), 'feedback_type': 'success'}
                    except (RuntimeError, AssertionError) as script_feedback:
                        response_data = {'message': script_feedback.message, 'feedback_type': 'error'}
                    if not response_data:
                        response_data = {'message': 'Custom taxonomy validated!', 'feedback_type': 'success'}
                else:
                    # Actually do the migration of the custom taxonomies
                    migrate(
                        provider=provider._id,
                        data=taxonomy_json,
                        provider_type='osf.registrationprovider',
                        add_missing=provider_form.cleaned_data['add_missing'])

                    return redirect('registration_providers:detail', registration_provider_id=provider.id)
            except (ValueError, RuntimeError) as error:
                response_data = {
                    'message': 'There is an error with the submitted JSON or the provider. Here are some details: ' + error.message,
                    'feedback_type': 'error'
                }
        else:
            response_data = {
                'message': 'There is a problem with the form. Here are some details: ' + unicode(provider_form.errors),
                'feedback_type': 'error'
            }
        # Return a JsonResponse with the JSON error or the validation error if it's not doing an actual migration
        return JsonResponse(response_data)
