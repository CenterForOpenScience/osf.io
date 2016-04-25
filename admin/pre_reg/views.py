from __future__ import unicode_literals

import json

from django.views.generic import ListView, DetailView, FormView, UpdateView
from django.views.defaults import permission_denied, bad_request
from django.core.urlresolvers import reverse
from django.http import JsonResponse, Http404
from django.shortcuts import redirect

from admin.common_auth.logs import (
    update_admin_log,
    ACCEPT_PREREG,
    REJECT_PREREG,
    COMMENT_PREREG,
)
from admin.pre_reg import serializers
from admin.pre_reg.forms import DraftRegistrationForm
from admin.pre_reg.utils import sort_drafts, build_query, SORT_BY, VIEW_STATUS
from framework.exceptions import PermissionsError
from website.exceptions import NodeStateError
from website.files.models import FileNode
from website.project.model import DraftRegistration

from admin.base.utils import PreregAdmin


class DraftListView(PreregAdmin, ListView):
    template_name = 'pre_reg/draft_list.html'
    ordering = 'n_date'
    context_object_name = 'draft'

    def get_queryset(self):
        query = build_query(self.request.GET.get('status', 'all'))
        ordering = self.get_ordering()
        if 'initiator' in ordering:
            return DraftRegistration.find(query).sort(ordering)
        return sort_drafts(DraftRegistration.find(query), ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'drafts': [
                serializers.serialize_draft_registration(d, json_safe=False)
                for d in query_set
            ],
            'page': page,
            'p': self.get_paginate_by(query_set),
            'SORT_BY': SORT_BY,
            'order': self.get_ordering(),
            'VIEW_STATUS': VIEW_STATUS,
            'status': self.request.GET.get('status', 'all')
        }

    def get_paginate_by(self, queryset):
        return int(self.request.GET.get('p', 10))

    def get_paginate_orphans(self):
        return int(self.get_paginate_by(None) / 11.0) + 1

    def get_ordering(self):
        return self.request.GET.get('order_by', self.ordering)


class DraftDetailView(PreregAdmin, DetailView):
    template_name = 'pre_reg/draft_detail.html'
    context_object_name = 'draft'

    def get_object(self, queryset=None):
        try:
            return serializers.serialize_draft_registration(
                DraftRegistration.load(self.kwargs.get('draft_pk'))
            )
        except AttributeError:
            raise Http404('{} with id "{}" not found.'.format(
                self.context_object_name.title(),
                self.kwargs.get('draft_pk')
            ))


class DraftFormView(PreregAdmin, FormView):
    template_name = 'pre_reg/draft_form.html'
    form_class = DraftRegistrationForm
    context_object_name = 'draft'

    def dispatch(self, request, *args, **kwargs):
        self.draft = DraftRegistration.load(self.kwargs.get('draft_pk'))
        if self.draft is None:
            raise Http404('{} with id "{}" not found.'.format(
                self.context_object_name.title(),
                self.kwargs.get('draft_pk')
            ))
        return super(DraftFormView, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        flags = self.draft.flags
        self.initial = {
            'notes': self.draft.notes,
            'assignee': flags.get('assignee'),
            'payment_sent': flags.get('payment_sent'),
            'proof_of_publication': flags.get('proof_of_publication'),
        }
        return super(DraftFormView, self).get_initial()

    def get_context_data(self, **kwargs):
        kwargs.setdefault('draft', serializers.serialize_draft_registration(
            self.draft,
            json_safe=False
        ))
        kwargs.setdefault('IMMEDIATE', serializers.IMMEDIATE)
        return super(DraftFormView, self).get_context_data(**kwargs)

    def form_valid(self, form):
        if 'approve_reject' in form.changed_data:
            osf_user = self.request.user.osf_user
            try:
                if form.cleaned_data.get('approve_reject') == 'approve':
                    flag = ACCEPT_PREREG
                    message = 'Approved'
                    self.draft.approve(osf_user)
                else:
                    flag = REJECT_PREREG
                    message = 'Rejected'
                    self.draft.reject(osf_user)
            except PermissionsError as e:
                return permission_denied(self.request, e)
            update_admin_log(self.request.user.id, self.kwargs.get('draft_pk'),
                             'Draft Registration', message, flag)
        admin_settings = form.cleaned_data
        self.draft.notes = admin_settings.get('notes', self.draft.notes)
        del admin_settings['approve_reject']
        del admin_settings['notes']
        self.draft.flags = admin_settings
        self.draft.save()
        return super(DraftFormView, self).form_valid(form)

    def get_success_url(self):
        return '{}?page={}'.format(reverse('pre_reg:prereg'),
                                   self.request.POST.get('page', 1))


class CommentUpdateView(PreregAdmin, UpdateView):
    context_object_name = 'draft'

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body).get('schema_data', {})
            draft = DraftRegistration.load(self.kwargs.get('draft_pk'))
            draft.update_metadata(data)
            draft.save()
            log_message = list()
            for key, value in data.iteritems():
                comments = data.get(key, {}).get('comments', [])
                for comment in comments:
                    log_message.append('{}: {}'.format(key, comment['value']))
            update_admin_log(
                user_id=request.user.id,
                object_id=draft._id,
                object_repr='Draft Registration',
                message='Comments: <p>{}</p>'.format('</p><p>'.join(log_message)),
                action_flag=COMMENT_PREREG
            )
            return JsonResponse(serializers.serialize_draft_registration(draft))
        except AttributeError:
            raise Http404('{} with id "{}" not found.'.format(
                self.context_object_name.title(),
                self.kwargs.get('draft_pk')
            ))
        except NodeStateError as e:
            return bad_request(request, e)


def view_file(request, node_id, provider, file_id):
    fp = FileNode.load(file_id)
    wb_url = fp.generate_waterbutler_url()
    return redirect(wb_url)
