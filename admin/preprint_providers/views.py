from __future__ import unicode_literals

import json

from django.core import serializers
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.views.generic import ListView, FormView, DetailView, View, CreateView
from django.views.generic.detail import SingleObjectMixin

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.forms.models import model_to_dict
from django.shortcuts import redirect

from admin.base import settings
from admin.base.utils import get_subject_rules, rules_to_subjects
from admin.base.forms import ImportFileForm
from admin.preprint_providers.forms import PreprintProviderForm, PreprintProviderSubjectForm
from osf.models import PreprintProvider, NodeLicense, Subject


class PreprintProviderList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'preprint_providers/list.html'
    ordering = 'name'
    permission_required = 'osf.view_preprint_provider'
    raise_exception = True
    model = PreprintProvider

    def get_queryset(self):
        return PreprintProvider.objects.all().sort(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'preprint_providers': query_set,
            'page': page,
            'logohost': settings.OSF_URL
        }


class GetSubjectDescendants(PermissionRequiredMixin, View):
    template_name = 'preprint_providers/detail.html'
    permission_required = 'osf.view_preprint_provider'
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
    permission_required = 'osf.view_preprint_provider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        rules = json.loads(request.GET['rules'])
        all_subjects = rules_to_subjects(rules)
        return JsonResponse({'subjects': [sub.id for sub in all_subjects]})


class PreprintProviderDisplay(PermissionRequiredMixin, DetailView):
    model = PreprintProvider
    template_name = 'preprint_providers/detail.html'
    permission_required = 'osf.view_preprint_provider'
    raise_exception = True

    def get_object(self, queryset=None):
        return PreprintProvider.objects.get(id=self.kwargs.get('preprint_provider_id'))

    def get_context_data(self, *args, **kwargs):
        preprint_provider = self.get_object()
        all_subjects = preprint_provider.all_subjects
        subject_ids = [subject.id for subject in all_subjects]

        preprint_provider_attributes = model_to_dict(preprint_provider)
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))

        # Modify licenses_acceptable to be a list of the  license name
        preprint_licenses = [
            NodeLicense.objects.get(id=identifier).name.encode('utf-8') for identifier in preprint_provider_attributes['licenses_acceptable']
        ]
        preprint_provider_attributes['licenses_acceptable'] = '; '.join(preprint_licenses)

        subject_html = '<ul class="three-cols">'
        for parent in preprint_provider.top_level_subjects:
            subject_html += '<li>{}</li>'.format(parent.text)
            child_html = '<ul>'
            for child in parent.children.all():
                if child in all_subjects:
                    child_html += '<li>{}</li>'.format(child.text)
                    grandchild_html = '<ul>'
                    for grandchild in child.children.all():
                        if grandchild in all_subjects:
                            grandchild_html += '<li>{}</li>'.format(grandchild.text)
                    grandchild_html += '</ul>'
                    child_html += grandchild_html

            child_html += '</ul>'
            subject_html += child_html

        subject_html += '</ul>'
        preprint_provider_attributes['subjects_acceptable'] = subject_html

        kwargs['preprint_provider'] = preprint_provider_attributes
        kwargs['subject_ids'] = subject_ids
        kwargs['logohost'] = settings.OSF_URL
        fields = model_to_dict(preprint_provider)
        kwargs['change_form'] = PreprintProviderForm(initial=fields)
        initial_subjects = {'toplevel_subjects': subject_ids, 'subjects_chosen': ', '.join(str(i) for i in subject_ids)}
        kwargs['subject_form'] = PreprintProviderSubjectForm(initial=initial_subjects)
        kwargs['import_form'] = ImportFileForm()

        return kwargs


class PreprintProviderDetail(PermissionRequiredMixin, View):
    permission_required = 'osf.view_preprint_provider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        view = PreprintProviderDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = PreprintProviderChangeForm.as_view()
        return view(request, *args, **kwargs)


class PreprintProviderChangeForm(PermissionRequiredMixin, SingleObjectMixin, FormView):
    form_class = PreprintProviderForm
    model = PreprintProvider
    permission_required = 'osf.change_preprint_provider'
    raise_exception = True

    def get_object(self, queryset=None):
        return PreprintProvider.objects.get(id=self.kwargs.get('preprint_provider_id'))

    def update_preprint_provider_attributes(self, preprint_provider):
        form = PreprintProviderForm(self.request.POST or None, instance=preprint_provider)

        if form.is_valid():
            form.save()

        self.object.refresh_from_db()
        return reverse('preprint_providers:detail', kwargs={'preprint_provider_id': self.object.pk})

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        self.object = self.get_object()
        self.update_preprint_provider_attributes(self.object)
        return super(PreprintProviderChangeForm, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('preprint_providers:detail', kwargs={'preprint_provider_id': self.object.pk})


class ExportPreprintProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprint_provider'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        preprint_provider = PreprintProvider.objects.get(id=self.kwargs['preprint_provider_id'])
        data = serializers.serialize("json", [preprint_provider])

        filename = '{}_export.json'.format(preprint_provider.name)

        response = HttpResponse(data, content_type='text/json')
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response


class ImportPreprintProvider(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprint_provider'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            file_str = self.parse_file(request.FILES['file'])
            file_json = json.loads(file_str)
            return JsonResponse(file_json[0]['fields'])

    def parse_file(self, f):
        parsed_file = ''
        for chunk in f.chunks():
            parsed_file += str(chunk)
        return parsed_file


class ProcessSubjects(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprint_provider'
    raise_exception = True

    def update_subjects_on_provider(self, subject_ids, *args, **kwargs):
        provider = PreprintProvider.objects.get(id=kwargs['preprint_provider_id'])
        subject_ids = filter(lambda subject: subject != '', subject_ids)
        subjects_selected = [Subject.objects.get(id=ident) for ident in subject_ids]

        rules = get_subject_rules(subjects_selected)
        provider.subjects_acceptable = rules
        provider.save()

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()

        subjects_selected = [sub.strip() for sub in request.POST['subjects_chosen'].split(',')]
        self.update_subjects_on_provider(subjects_selected, *args, **kwargs)

        return redirect(reverse('preprint_providers:detail', kwargs=kwargs))


class SubjectDynamicUpdateView(PermissionRequiredMixin, View):
    permission_required = 'osf.change_preprint_provider'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        parent_id = request.GET['parent_id']
        level = request.GET.get('level', None)
        subjects_from_parent = Subject.objects.filter(parents__id=parent_id)
        subject_ids = [sub.id for sub in subjects_from_parent]

        new_level = 'secondlevel_subjects'
        if level == 'secondlevel_subjects':
            new_level = 'thirdlevel_subjects'

        subject_html = '<ul class="other-levels" style="list-style-type:none">'
        for subject in subjects_from_parent:
            subject_html += '<li><label><input type="checkbox" name="{}" value="{}">{}</label>'.format(new_level, subject.id, subject.text)
            if subject.children.count():
                    subject_html += '<i class="subject-icon glyphicon glyphicon-menu-right"></i>'
            subject_html += '</li>'
        subject_html += '</ul>'

        return JsonResponse({'html': subject_html, 'subject_ids': subject_ids})


class CreatePreprintProvider(PermissionRequiredMixin, CreateView):
    permission_required = 'osf.change_preprint_provider'
    raise_exception = True
    template_name = 'preprint_providers/create.html'
    success_url = reverse_lazy('preprint_providers:list')
    model = PreprintProvider

    def get_context_data(self, *args, **kwargs):
        kwargs['import_form'] = ImportFileForm()
        return super(CreatePreprintProvider, self).get_context_data(*args, **kwargs)

    fields = [
        'name', 'logo_name', 'header_text', 'description', 'banner_name',
        'external_url', 'email_contact', 'email_support', 'example', 'access_token',
        'advisory_board', 'social_twitter', 'social_facebook', 'licenses_acceptable'
    ]
