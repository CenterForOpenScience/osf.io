from __future__ import unicode_literals

import json


from django.http import Http404
from django.core import serializers
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, View, CreateView, DeleteView, TemplateView, UpdateView
from django.views.generic.edit import FormView
from django.core.management import call_command
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.forms.models import model_to_dict
from django.shortcuts import redirect, render

from admin.base import settings
from admin.base.forms import ImportFileForm
from admin.preprint_providers.forms import PreprintProviderForm, PreprintProviderCustomTaxonomyForm, PreprintProviderRegisterModeratorOrAdminForm
from osf.models import PreprintProvider, Subject, NodeLicense, OSFUser
from osf.models.provider import rules_to_subjects, WhitelistedSHAREPreprintProvider
from website import settings as website_settings

FIELDS_TO_NOT_IMPORT_EXPORT = ['access_token', 'share_source', 'subjects_acceptable', 'primary_collection']


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

        kwargs['preprint_provider_id'] = preprint_provider._id
        kwargs['preprint_provider'] = preprint_provider_attributes
        kwargs['subject_ids'] = list(subject_ids)
        kwargs['logo'] = preprint_provider.get_asset_url('square_color_no_transparent')
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
    template_name = 'preprint_providers/create_or_update_preprint_provider_form.html'
    raise_exception = True
    model = PreprintProvider
    form_class = PreprintProviderForm

    def get_object(self, queryset=None):
        provider_id = self.kwargs.get('preprint_provider_id')
        return PreprintProvider.objects.get(id=provider_id)

    def get_subject_ids(self, request, *args, **kwargs):
        parent_id = request.GET.get('parent_id')
        subjects_from_parent = Subject.objects.filter(parent__id=parent_id)
        subject_ids = [sub.id for sub in subjects_from_parent]
        return subject_ids

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        kwargs['preprint_provider_id'] = self.kwargs.get('preprint_provider_id')
        kwargs['tinymce_apikey'] = settings.TINYMCE_APIKEY
        kwargs['subject_ids'] = self.get_subject_ids(self.request)
        return super(PreprintProviderChangeForm, self).get_context_data(*args, **kwargs)

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('preprint_providers:detail', kwargs={'preprint_provider_id': self.kwargs.get('preprint_provider_id')})


class ProcessCustomTaxonomy(PermissionRequiredMixin, View):
    template_name = 'preprint_providers/enter_custom_taxonomy.html'
    permission_required = 'osf.change_preprintprovider'
    raise_exception = True
    form_class = PreprintProviderCustomTaxonomyForm

    def post(self, request, *args, **kwargs):
        # Import here to avoid test DB access errors when importing preprint provider views
        from osf.management.commands.populate_custom_taxonomies import validate_input, migrate

        provider_form = PreprintProviderCustomTaxonomyForm(request.POST)
        if provider_form.is_valid():
            provider = PreprintProvider.objects.get(id=request.POST.get('provider_id'))
            try:
                taxonomy_json = json.loads(provider_form.cleaned_data['custom_taxonomy_json'])
                if request.is_ajax():
                    # An ajax request is for validation only, so run that validation!
                    response_data = validate_input(custom_provider=provider, data=taxonomy_json, add_missing=provider_form.cleaned_data['add_missing'])
                    if response_data:
                        added_subjects = [subject.text for subject in response_data]
                        messages.success(f'Custom taxonomy validated with added subjects: {added_subjects}')
                else:
                    # Actually do the migration of the custom taxonomies
                    migrate(provider=provider._id, data=taxonomy_json, add_missing=provider_form.cleaned_data['add_missing'])
                    return redirect('preprint_providers:detail', preprint_provider_id=provider.id)
            except (ValueError, RuntimeError, AssertionError) as error:
                messages.error(request, f'There is an error with the submitted JSON or the provider. Here are some details: {str(error)}')
        else:
            for key, value in provider_form.errors.items():
                messages.error(request, f'{key}: {value}')

        return redirect(
            reverse_lazy(
                'preprint_providers:process_custom_taxonomy',
                kwargs={
                    'preprint_provider_id': kwargs.get('preprint_provider_id')
                }
            )
        )

    def get_subjects(self, request, *args, **kwargs):
        parent_id = request.GET.get('parent_id')
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

        return {
            'html': subject_html,
            'subject_ids': subject_ids
        }

    def get(self, request, *args, **kwargs):
        data = self.get_subjects(request)
        preprint_provider = PreprintProvider.objects.get(id=int(self.kwargs.get('preprint_provider_id')))
        return render(
            request,
            self.template_name,
            {
                'preprint_provider_id': self.kwargs.get('preprint_provider_id'),
                'subject_ids': data['subject_ids'],
                'taxonomy_form': PreprintProviderCustomTaxonomyForm(),
                'taxonomies_created': False if not preprint_provider.subjects.exists() else True
            }
        )

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('preprint_providers:process_custom_taxonomy', kwargs={'preprint_provider_id': self.kwargs.get('preprint_provider_id')})


class ExportPreprintProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprintprovider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        preprint_provider = PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id'])
        data = serializers.serialize('json', [preprint_provider])
        cleaned_data = json.loads(data)[0]
        cleaned_fields = {key: value for key, value in cleaned_data['fields'].items() if key not in FIELDS_TO_NOT_IMPORT_EXPORT}
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
        if preprint_provider.preprints.count() > 0:
            return redirect('preprint_providers:cannot_delete', preprint_provider_id=preprint_provider.pk)
        return super(DeletePreprintProvider, self).delete(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        preprint_provider = PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id'])
        if preprint_provider.preprints.count() > 0:
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
            cleaned_result = {key: value for key, value in file_json['fields'].items() if key not in FIELDS_TO_NOT_IMPORT_EXPORT and key in current_fields}
            try:
                preprint_provider = self.create_or_update_provider(cleaned_result)
            except ValidationError:
                messages.error(request, 'A Validation Error occured, this JSON is invalid or shares an id with an already existing provider.')
                return redirect('preprint_providers:create')

            return redirect('preprint_providers:detail', preprint_provider_id=preprint_provider.id)

    def parse_file(self, f):
        parsed_file = ''
        for chunk in f.chunks():
            if isinstance(chunk, bytes):
                chunk = chunk.decode()
            parsed_file += chunk
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
            for key, val in provider_data.items():
                setattr(provider, key, val)
        else:
            provider = PreprintProvider(**provider_data)

        provider.save()

        if licenses:
            provider.licenses_acceptable.set(licenses)
        if default_license:
            provider.default_license = NodeLicense.objects.get(license_id=default_license)
        # Only adds the JSON taxonomy if there is no existing taxonomy data
        if subject_data and not provider.subjects.count():
            self.add_subjects(provider, subject_data)
        return provider


class ShareSourcePreprintProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprintprovider'
    view_category = 'preprint_providers'

    def get(self, request, *args, **kwargs):
        provider = PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id'])
        home_page_url = provider.domain if provider.domain else f'{website_settings.DOMAIN}/preprints/{provider._id}/'

        try:
            provider.setup_share_source(home_page_url)
        except ValidationError as e:
            messages.error(request, e.message)

        return redirect(reverse_lazy('preprint_providers:share_source', kwargs={'preprint_provider_id': provider.id}))

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
    template_name = 'preprint_providers/create_or_update_preprint_provider_form.html'
    success_url = reverse_lazy('preprint_providers:list')
    model = PreprintProvider
    form_class = PreprintProviderForm

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        kwargs['show_taxonomies'] = False
        kwargs['tinymce_apikey'] = settings.TINYMCE_APIKEY
        return super(CreatePreprintProvider, self).get_context_data(*args, **kwargs)


class SharePreprintProviderWhitelist(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprintprovider'
    raise_exception = True
    template_name = 'preprint_providers/whitelist.html'

    def post(self, request):
        providers_added = json.loads(request.body).get('added')
        if len(providers_added) != 0:
            for item in providers_added:
                WhitelistedSHAREPreprintProvider.objects.get_or_create(provider_name=item)
        return HttpResponse(200)

    def delete(self, request):
        providers_removed = json.loads(request.body).get('removed')
        if len(providers_removed) != 0:
            for item in providers_removed:
                WhitelistedSHAREPreprintProvider.objects.get(provider_name=item).delete()
        return HttpResponse(200)

    def get(self, request):
        share_api_url = settings.SHARE_URL
        api_v2_url = settings.API_DOMAIN + settings.API_BASE
        return render(request, self.template_name, {'share_api_url': share_api_url, 'api_v2_url': api_v2_url})


class PreprintProviderRegisterModeratorOrAdmin(PermissionRequiredMixin, FormView):
    permission_required = 'osf.change_preprintprovider'
    raise_exception = True
    template_name = 'preprint_providers/register_moderator_admin.html'
    form_class = PreprintProviderRegisterModeratorOrAdminForm

    def get_form_kwargs(self):
        kwargs = super(PreprintProviderRegisterModeratorOrAdmin, self).get_form_kwargs()
        kwargs['provider_id'] = self.kwargs['preprint_provider_id']
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(PreprintProviderRegisterModeratorOrAdmin, self).get_context_data(**kwargs)
        context['provider_name'] = PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id']).name
        return context

    def form_valid(self, form):
        user_id = form.cleaned_data.get('user_id')
        osf_user = OSFUser.load(user_id)

        if not osf_user:
            raise Http404('OSF user with id "{}" not found. Please double check.'.format(user_id))

        for group in form.cleaned_data.get('group_perms'):
            osf_user.groups.add(group)
            split = group.name.split('_')
            group_type = split[0]
            if group_type == 'reviews':
                provider_id = split[2]
                provider = PreprintProvider.objects.get(id=provider_id)
                provider.notification_subscriptions.get(event_name='new_pending_submissions').add_user_to_subscription(osf_user, 'email_transactional')

        osf_user.save()
        messages.success(self.request, 'Permissions update successful for OSF User {}!'.format(osf_user.username))
        return super(PreprintProviderRegisterModeratorOrAdmin, self).form_valid(form)

    def get_success_url(self):
        return reverse('preprint_providers:register_moderator_admin', kwargs={'preprint_provider_id': self.kwargs['preprint_provider_id']})
