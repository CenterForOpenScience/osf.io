from __future__ import unicode_literals

import json
import requests
import urlparse

from django.core import serializers
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, View, CreateView, DeleteView, TemplateView, UpdateView
from django.core.management import call_command
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.forms.models import model_to_dict
from django.shortcuts import redirect

from website import settings as web_settings
from admin.base import settings
from admin.base.forms import ImportFileForm
from admin.preprint_providers.forms import PreprintProviderForm, PreprintProviderCustomTaxonomyForm
from osf.models import PreprintProvider, Subject, NodeLicense
from osf.models.provider import rules_to_subjects
from website import settings as osf_settings

# When preprint_providers exclusively use Subject relations for creation, set this to False
SHOW_TAXONOMIES_IN_PREPRINT_PROVIDER_CREATE = True
FIELDS_TO_NOT_IMPORT_EXPORT = ['access_token', 'share_source', 'subjects_acceptable']


class PreprintProviderList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'preprint_providers/list.html'
    ordering = 'name'
    permission_required = 'osf.view_preprintprovider'
    raise_exception = True
    model = PreprintProvider

    def get_queryset(self):
        return PreprintProvider.objects.all().order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'preprint_providers': query_set,
            'page': page,
        }


class GetSubjectDescendants(PermissionRequiredMixin, View):
    template_name = 'preprint_providers/detail.html'
    permission_required = 'osf.view_preprintprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        parent_id = request.GET['parent_id']
        direct_children = Subject.objects.get(id=parent_id).children.all()
        grandchildren = []
        for child in direct_children:
            grandchildren += child.children.all()
        all_descendants = list(direct_children) + grandchildren

        return JsonResponse({'all_descendants': [sub.id for sub in all_descendants]})


class RulesToSubjects(PermissionRequiredMixin, View):
    permission_required = 'osf.view_preprintprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        rules = json.loads(request.GET['rules'])
        all_subjects = rules_to_subjects(rules)
        return JsonResponse({'subjects': [sub.id for sub in all_subjects]})


class PreprintProviderDisplay(PermissionRequiredMixin, DetailView):
    model = PreprintProvider
    template_name = 'preprint_providers/detail.html'
    permission_required = 'osf.view_preprintprovider'
    raise_exception = True

    def get_object(self, queryset=None):
        return PreprintProvider.objects.get(id=self.kwargs.get('preprint_provider_id'))

    def get_context_data(self, *args, **kwargs):
        preprint_provider = self.get_object()
        subject_ids = preprint_provider.all_subjects.values_list('id', flat=True)

        preprint_provider_attributes = model_to_dict(preprint_provider)
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))

        licenses_acceptable = list(preprint_provider.licenses_acceptable.values_list('name', flat=True))
        licenses_html = '<ul>'
        for license in licenses_acceptable:
            licenses_html += '<li>{}</li>'.format(license)
        licenses_html += '</ul>'
        preprint_provider_attributes['licenses_acceptable'] = licenses_html

        subject_html = '<ul class="three-cols">'
        for parent in preprint_provider.top_level_subjects:
            mapped_text = ''
            if parent.bepress_subject and parent.text != parent.bepress_subject.text:
                mapped_text = ' (mapped from {})'.format(parent.bepress_subject.text)
            subject_html = subject_html + '<li>{}'.format(parent.text) + mapped_text + '</li>'
            child_html = '<ul>'
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
        preprint_provider_attributes['subjects_acceptable'] = subject_html
        preprint_provider_attributes['lower_name'] = preprint_provider._id

        kwargs['preprint_provider'] = preprint_provider_attributes
        kwargs['subject_ids'] = list(subject_ids)
        kwargs['logohost'] = urlparse.urljoin(web_settings.DOMAIN, web_settings.PREPRINTS_ASSETS)
        fields = model_to_dict(preprint_provider)
        fields['toplevel_subjects'] = list(subject_ids)
        fields['subjects_chosen'] = ', '.join(str(i) for i in subject_ids)
        kwargs['show_taxonomies'] = False if preprint_provider.subjects.exists() else True
        kwargs['form'] = PreprintProviderForm(initial=fields)
        kwargs['taxonomy_form'] = PreprintProviderCustomTaxonomyForm()
        kwargs['import_form'] = ImportFileForm()
        kwargs['tinymce_apikey'] = settings.TINYMCE_APIKEY
        return kwargs


class PreprintProviderDetail(PermissionRequiredMixin, View):
    permission_required = 'osf.view_preprintprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        view = PreprintProviderDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = PreprintProviderChangeForm.as_view()
        return view(request, *args, **kwargs)


class PreprintProviderChangeForm(PermissionRequiredMixin, UpdateView):
    permission_required = 'osf.change_preprintprovider'
    raise_exception = True
    model = PreprintProvider
    form_class = PreprintProviderForm

    def get_object(self, queryset=None):
        provider_id = self.kwargs.get('preprint_provider_id')
        return PreprintProvider.objects.get(id=provider_id)

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        return super(PreprintProviderChangeForm, self).get_context_data(*args, **kwargs)

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('preprint_providers:detail', kwargs={'preprint_provider_id': self.kwargs.get('preprint_provider_id')})


class ProcessCustomTaxonomy(PermissionRequiredMixin, View):

    permission_required = 'osf.change_preprintprovider'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        # Import here to avoid test DB access errors when importing preprint provider views
        from osf.management.commands.populate_custom_taxonomies import validate_input, migrate

        provider_form = PreprintProviderCustomTaxonomyForm(request.POST)
        if provider_form.is_valid():
            provider = PreprintProvider.objects.get(id=provider_form.cleaned_data['provider_id'])
            try:
                taxonomy_json = json.loads(provider_form.cleaned_data['custom_taxonomy_json'])
                if request.is_ajax():
                    # An ajax request is for validation only, so run that validation!
                    try:
                        response_data = validate_input(custom_provider=provider, data=taxonomy_json, add_missing=provider_form.cleaned_data['add_missing'])
                        if response_data:
                            added_subjects = [subject.text for subject in response_data]
                            response_data = {'message': 'Custom taxonomy validated with added subjects: {}'.format(added_subjects), 'feedback_type': 'success'}
                    except (RuntimeError, AssertionError) as script_feedback:
                        response_data = {'message': script_feedback.message, 'feedback_type': 'error'}
                    if not response_data:
                        response_data = {'message': 'Custom taxonomy validated!', 'feedback_type': 'success'}
                else:
                    # Actually do the migration of the custom taxonomies
                    migrate(provider=provider._id, data=taxonomy_json, add_missing=provider_form.cleaned_data['add_missing'])
                    return redirect('preprint_providers:detail', preprint_provider_id=provider.id)
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

class ExportPreprintProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprintprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        preprint_provider = PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id'])
        data = serializers.serialize('json', [preprint_provider])
        cleaned_data = json.loads(data)[0]
        cleaned_fields = {key: value for key, value in cleaned_data['fields'].iteritems() if key not in FIELDS_TO_NOT_IMPORT_EXPORT}
        cleaned_fields['licenses_acceptable'] = [node_license.license_id for node_license in preprint_provider.licenses_acceptable.all()]
        cleaned_fields['default_license'] = preprint_provider.default_license.license_id if preprint_provider.default_license else ''
        cleaned_fields['subjects'] = self.serialize_subjects(preprint_provider)
        cleaned_data['fields'] = cleaned_fields
        filename = '{}_export.json'.format(preprint_provider.name)
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

class DeletePreprintProvider(PermissionRequiredMixin, DeleteView):
    permission_required = 'osf.delete_preprintprovider'
    raise_exception = True
    template_name = 'preprint_providers/confirm_delete.html'
    success_url = reverse_lazy('preprint_providers:list')

    def delete(self, request, *args, **kwargs):
        preprint_provider = PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id'])
        if preprint_provider.preprint_services.count() > 0:
            return redirect('preprint_providers:cannot_delete', preprint_provider_id=preprint_provider.pk)
        return super(DeletePreprintProvider, self).delete(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        preprint_provider = PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id'])
        if preprint_provider.preprint_services.count() > 0:
            return redirect('preprint_providers:cannot_delete', preprint_provider_id=preprint_provider.pk)
        return super(DeletePreprintProvider, self).get(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id'])


class CannotDeleteProvider(TemplateView):
    template_name = 'preprint_providers/cannot_delete.html'

    def get_context_data(self, **kwargs):
        context = super(CannotDeleteProvider, self).get_context_data(**kwargs)
        context['provider'] = PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id'])
        return context


class ImportPreprintProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprintprovider'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_str = self.parse_file(request.FILES['file'])
            file_json = json.loads(file_str)
            current_fields = [f.name for f in PreprintProvider._meta.get_fields()]
            # make sure not to import an exported access token for SHARE
            cleaned_result = {key: value for key, value in file_json['fields'].iteritems() if key not in FIELDS_TO_NOT_IMPORT_EXPORT and key in current_fields}
            preprint_provider = self.create_or_update_provider(cleaned_result)
            return redirect('preprint_providers:detail', preprint_provider_id=preprint_provider.id)

    def parse_file(self, f):
        parsed_file = ''
        for chunk in f.chunks():
            parsed_file += chunk.decode('utf-8')
        return parsed_file

    def get_page_provider(self):
        page_provider_id = self.kwargs.get('preprint_provider_id', '')
        if page_provider_id:
            return PreprintProvider.objects.get(id=page_provider_id)

    def add_subjects(self, provider, subject_data):
        call_command('populate_custom_taxonomies', '--provider', provider._id, '--data', json.dumps(subject_data))

    def create_or_update_provider(self, provider_data):
        provider = self.get_page_provider()
        licenses = [NodeLicense.objects.get(license_id=license_id) for license_id in provider_data.pop('licenses_acceptable', [])]
        default_license = provider_data.pop('default_license', False)
        subject_data = provider_data.pop('subjects', False)

        if provider:
            for key, val in provider_data.iteritems():
                setattr(provider, key, val)
        else:
            provider = PreprintProvider(**provider_data)

        provider.save()

        if licenses:
            provider.licenses_acceptable = licenses
        if default_license:
            provider.default_license = NodeLicense.objects.get(license_id=default_license)
        # Only adds the JSON taxonomy if there is no existing taxonomy data
        if subject_data and not provider.subjects.count():
            self.add_subjects(provider, subject_data)
        return provider


class ShareSourcePreprintProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprintprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        preprint_provider = PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id'])

        resp_json = self.share_post(preprint_provider)
        for data in resp_json['included']:
            if data['type'] == 'ShareUser':
                preprint_provider.access_token = data['attributes']['token']
            elif data['type'] == 'SourceConfig':
                preprint_provider.share_source = data['attributes']['label']
        preprint_provider.save()
        return redirect(reverse_lazy('preprint_providers:detail', kwargs={'preprint_provider_id': preprint_provider.id}))

    def share_post(self, preprint_provider):
        if preprint_provider.share_source or preprint_provider.access_token:
            raise ValueError('Cannot update share_source or access_token because one or the other already exists')
        if not osf_settings.SHARE_API_TOKEN or not osf_settings.SHARE_URL:
            raise ValueError('SHARE_API_TOKEN or SHARE_URL not set')

        debug_prepend = ''
        if osf_settings.DEBUG_MODE or osf_settings.SHARE_PREPRINT_PROVIDER_PREPEND:
            assert osf_settings.SHARE_PREPRINT_PROVIDER_PREPEND, 'Local SHARE_PREPRINT_PROVIDER_PREPEND (e.g., \'alexschiller\') must be set when in DEBUG_MODE'
            debug_prepend = '{}_'.format(osf_settings.SHARE_PREPRINT_PROVIDER_PREPEND)

        return requests.post(
            '{}api/v2/sources/'.format(osf_settings.SHARE_URL),
            json={
                'data': {
                    'type': 'Source',
                    'attributes': {
                        'homePage': preprint_provider.domain if preprint_provider.domain else '{}/preprints/{}/'.format(osf_settings.DOMAIN, preprint_provider._id),
                        'longTitle': debug_prepend + preprint_provider.name,
                        'iconUrl': '{}{}{}/square_color_no_transparent.png'.format(settings.OSF_URL, osf_settings.PREPRINTS_ASSETS, preprint_provider._id)
                    }
                }
            },
            headers={
                'Authorization': 'Bearer {}'.format(osf_settings.SHARE_API_TOKEN),
                'Content-Type': 'application/vnd.api+json'
            }
        ).json()


class SubjectDynamicUpdateView(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprintprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        parent_id = request.GET['parent_id']
        level = request.GET.get('level', None)
        subjects_from_parent = Subject.objects.filter(parent__id=parent_id)
        subject_ids = [sub.id for sub in subjects_from_parent]

        new_level = 'secondlevel_subjects'
        if level == 'secondlevel_subjects':
            new_level = 'thirdlevel_subjects'

        subject_html = '<ul class="other-levels" style="list-style-type:none">'
        for subject in subjects_from_parent:
            subject_html += '<li><label><input type="checkbox" name="{}" value="{}" parent={}>{}</label>'.format(new_level, subject.id, parent_id, subject.text)
            if subject.children.count():
                    subject_html += '<i class="subject-icon glyphicon glyphicon-menu-right"></i>'
            subject_html += '</li>'
        subject_html += '</ul>'

        return JsonResponse({'html': subject_html, 'subject_ids': subject_ids})


class CreatePreprintProvider(PermissionRequiredMixin, CreateView):
    permission_required = 'osf.change_preprintprovider'
    raise_exception = True
    template_name = 'preprint_providers/create.html'
    success_url = reverse_lazy('preprint_providers:list')
    model = PreprintProvider
    form_class = PreprintProviderForm

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        kwargs['show_taxonomies'] = SHOW_TAXONOMIES_IN_PREPRINT_PROVIDER_CREATE
        kwargs['tinymce_apikey'] = settings.TINYMCE_APIKEY
        return super(CreatePreprintProvider, self).get_context_data(*args, **kwargs)
