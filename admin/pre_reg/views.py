from __future__ import unicode_literals

import httplib as http
import json

from django.views.generic import ListView, DetailView, FormView
from django.views.defaults import page_not_found, permission_denied
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from modularodm import Q

from admin.common_auth.logs import (
    update_admin_log,
    ACCEPT_PREREG,
    REJECT_PREREG,
    COMMENT_PREREG,
)
from admin.pre_reg import serializers
from admin.pre_reg.forms import DraftRegistrationForm
from framework.exceptions import HTTPError, PermissionsError
from website.exceptions import NodeStateError
from website.files.models import FileNode
from website.project.model import MetaSchema, DraftRegistration

from admin.base.utils import PreregAdmin


class DraftListView(PreregAdmin, ListView):
    template_name = 'pre_reg/draft_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = '-approval.initiation_date'
    context_object_name = 'draft'

    def get_queryset(self):
        prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
        query = (
            Q('registration_schema', 'eq', prereg_schema) &
            Q('approval', 'ne', None)
        )
        return DraftRegistration.find(query).sort(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'drafts': [serializers.serialize_draft_registration(d, json_safe=False) for d in query_set],
            'page': page,
        }


class DraftDetailView(PreregAdmin, DetailView):
    template_name = 'pre_reg/edit_draft_registration.html'
    context_object_name = 'draft'

    def get(self, request, *args, **kwargs):
        try:
            return super(DraftDetailView, self).get(request, *args, **kwargs)
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        kwargs.get('draft_pk')
                    )
                )
            )

    def get_object(self, queryset=None):
        return serializers.serialize_draft_registration(
            DraftRegistration.load(self.kwargs.get('draft_pk'), json_safe=False)
        )


class DraftFormView(PreregAdmin, FormView):
    template_name = 'pre_reg/draft_form.html'
    form_class = DraftRegistrationForm
    context_object_name = 'draft'

    def get(self, request, *args, **kwargs):
        try:
            return super(DraftFormView, self).get(request, *args, **kwargs)
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        kwargs.get('draft_pk')
                    )
                )
            )

    def post(self, request, *args, **kwargs):
        try:
            return super(DraftFormView, self).post(request, *args, **kwargs)
        except AttributeError:
            return page_not_found(
                request,
                AttributeError(
                    '{} with id "{}" not found.'.format(
                        self.context_object_name.title(),
                        kwargs.get('draft_pk')
                    )
                )
            )
        except PermissionsError as e:
            return permission_denied(request, e)

    def get_initial(self):
        draft = DraftRegistration.load(self.kwargs.get('draft_pk'))
        flags = draft.flags
        self.initial = {
            'notes': draft.notes,
            'assignee': flags['assignee'],
            'payment_sent': flags['payment_sent'],
            'proof_of_publication': flags['proof_of_publication'],
        }
        return super(DraftFormView, self).get_initial()

    def get_context_data(self, **kwargs):
        kwargs.setdefault('draft', serializers.serialize_draft_registration(
            DraftRegistration.load(self.kwargs.get('draft_pk')),
            json_safe=False
        ))
        kwargs.setdefault('IMMEDIATE', serializers.IMMEDIATE)
        return super(DraftFormView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        draft = DraftRegistration.load(self.kwargs.get('draft_pk'))
        if 'approve_reject' in form.changed_data:
            osf_user = self.request.user.osf_user
            if form.cleaned_data.get('approve_reject') == 'approve':
                flag = ACCEPT_PREREG
                message = 'Approved'
                draft.approve(osf_user)
            else:
                flag = REJECT_PREREG
                message = 'Rejected'
                draft.reject(osf_user)
            update_admin_log(self.request.user.id, self.kwargs.get('draft_pk'),
                             'Draft Registration', message, flag)
        admin_settings = form.cleaned_data
        draft.notes = admin_settings.get('notes', draft.notes)
        del admin_settings['approve_reject']
        del admin_settings['notes']
        draft.flags = admin_settings
        draft.save()
        return super(DraftFormView, self).form_valid(form)

    def get_success_url(self):
        return '{}?page={}'.format(reverse('pre_reg:prereg'),
                                   self.request.POST.get('page', 1))


def view_file(request, node_id, provider, file_id):
    file = FileNode.load(file_id)
    wb_url = file.generate_waterbutler_url()
    return redirect(wb_url)


@csrf_exempt
def update_draft(request, draft_pk):
    """Updates current draft to save admin comments

    :param draft_pk: Unique id for current draft
    :return: DraftRegistration obj
    """
    data = json.loads(request.body)
    draft = get_draft_or_error(draft_pk)

    if 'admin_settings' in data:
        form = DraftRegistrationForm(data=data['admin_settings'])
        if not form.is_valid():
            return HttpResponseBadRequest("Invalid form data")
        admin_settings = form.cleaned_data
        draft.notes = admin_settings.get('notes', draft.notes)
        del admin_settings['notes']
        draft.flags = admin_settings
        draft.save()
    else:
        schema_data = data.get('schema_data', {})
        log_message = list()
        for key, value in schema_data.iteritems():
            comments = schema_data.get(key, {}).get('comments', [])
            for comment in comments:
                log_message.append('{}: {}'.format(key, comment['value']))
        try:
            draft.update_metadata(schema_data)
            draft.save()
            update_admin_log(
                user_id=request.user.id,
                object_id=draft._id,
                object_repr='Draft Registration',
                message='Comments: <p>{}</p>'.format('</p><p>'.join(log_message)),
                action_flag=COMMENT_PREREG
            )
        except (NodeStateError):
            raise HTTPError(http.BAD_REQUEST)
    return JsonResponse(serializers.serialize_draft_registration(draft))
