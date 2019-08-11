from __future__ import unicode_literals

import json

from django.views.generic import ListView, DeleteView, DetailView, FormView, UpdateView
from django.views.defaults import permission_denied, bad_request
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.urlresolvers import reverse
from django.http import JsonResponse, Http404
from django.shortcuts import redirect

from osf.models.admin_log_entry import (
    update_admin_log,
    ACCEPT_PREREG,
    REJECT_PREREG,
    COMMENT_PREREG,
    CHECKOUT_CHECKUP,
)

from admin.pre_reg import serializers
from admin.pre_reg.forms import DraftRegistrationForm
from framework.exceptions import PermissionsError
from osf.exceptions import NodeStateError

from osf.models import (
    BaseFileNode,
    DraftRegistration,
    RegistrationSchema,
    Node,
    OSFUser,
)
from website.project.metadata.schemas import from_json
from website.prereg.utils import get_prereg_schema


SORT_BY = {
    'initiator': 'initiator__fullname',
    'n_initiator': '-initiator__fullname',
    'title': 'branched_from__title',
    'n_title': '-branched_from__title',
    'date': 'approval__initiation_date',
    'n_date': '-approval__initiation_date',
    'state': 'approval__state',
    'n_state': '-approval__state',
}


class DraftListView(PermissionRequiredMixin, ListView):
    template_name = 'pre_reg/draft_list.html'
    ordering = '-approval__initiation_date'
    context_object_name = 'draft'
    permission_required = 'osf.view_prereg'
    raise_exception = True

    def get_queryset(self):
        return DraftRegistration.objects.filter(
            registration_schema=get_prereg_schema(),
            approval__isnull=False,
        ).order_by(self.get_ordering())

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
            'status': self.request.GET.get('status', 'all'),
        }

    def get_paginate_by(self, queryset):
        return int(self.request.GET.get('p', 10))

    def get_paginate_orphans(self):
        return int(self.get_paginate_by(None) / 11.0) + 1

    def get_ordering(self):
        return self.request.GET.get('order_by', self.ordering)


class CheckoutCheckupView(PermissionRequiredMixin, DeleteView):
    """ View for button that checks status of all prereg drafts and removes checkouts that lingered beyond approval/rejection"""
    template_name = 'pre_reg/checkout_checkup.html'
    permission_required = 'osf.view_prereg'
    raise_exception = True

    def get_context_data(self, **kwargs):
        context = {}
        context.setdefault('bad_drafts_count', str(self.get_object().count()))
        return super(CheckoutCheckupView, self).get_context_data(**context)

    def get_object(self, queryset=None):
        self.prereg_admins = OSFUser.objects.filter(groups__name='prereg_view')
        self.bad_drafts = DraftRegistration.objects.filter(
            registration_schema=RegistrationSchema.objects.get(name='Prereg Challenge', schema_version=2),
            approval__state__in=['approved', 'rejected'],
            branched_from__files__checkout__in=self.prereg_admins
        ).distinct().values_list('id', flat=True)
        return self.bad_drafts

    def delete(self, request, *args, **kwargs):
        if not self.get('bad_drafts', None):
            self.get_object()

        for draft_id in self.bad_drafts:
            draft = DraftRegistration.objects.get(id=draft_id)
            for draft_file in draft.branched_from.files.filter(checkout__in=self.prereg_admins):
                draft_file.checkout = None
                draft_file.save()

            update_admin_log(
                user_id=self.request.user.id,
                object_id=draft.branched_from._id,
                object_repr='Node',
                message='Cleared Prereg checkouts from {}'.format(draft.branched_from._id),
                action_flag=CHECKOUT_CHECKUP
            )
        return redirect(reverse('pre_reg:prereg'))


class DraftDetailView(PermissionRequiredMixin, DetailView):
    template_name = 'pre_reg/draft_detail.html'
    context_object_name = 'draft'
    permission_required = 'osf.view_prereg'
    raise_exception = True

    def get_object(self, queryset=None):
        draft = DraftRegistration.objects.select_related('approval').get(_id=self.kwargs.get('draft_pk'))
        self.checkout_files(draft)
        try:
            return serializers.serialize_draft_registration(draft)
        except AttributeError:
            raise Http404('{} with id "{}" not found.'.format(
                self.context_object_name.title(),
                self.kwargs.get('draft_pk')
            ))

    def checkout_files(self, draft):
        # Do not check out files if rejected or approved
        if not draft.approval or draft.approval.state == 'unapproved':
            prereg_user = self.request.user
            for item in get_metadata_files(draft):
                item.checkout = prereg_user
                item.save()


class DraftFormView(PermissionRequiredMixin, FormView):
    template_name = 'pre_reg/draft_form.html'
    form_class = DraftRegistrationForm
    context_object_name = 'draft'
    permission_required = 'osf.view_prereg'
    raise_exception = True

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
            osf_user = self.request.user
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
            self.checkin_files(self.draft)
            update_admin_log(self.request.user.id, self.kwargs.get('draft_pk'),
                             'Draft Registration', message, flag)
        admin_settings = form.cleaned_data
        self.draft.notes = admin_settings.get('notes', self.draft.notes)
        del admin_settings['approve_reject']
        del admin_settings['notes']
        self.draft.flags = admin_settings
        self.draft.save()
        return super(DraftFormView, self).form_valid(form)

    def checkin_files(self, draft):
        for item in get_metadata_files(draft):
            item.checkout = None
            item.save()

    def get_success_url(self):
        return '{}?page={}'.format(reverse('pre_reg:prereg'),
                                   self.request.POST.get('page', 1))


class CommentUpdateView(PermissionRequiredMixin, UpdateView):
    context_object_name = 'draft'
    permission_required = ('osf.view_prereg', 'osf.administer_prereg')
    raise_exception = True

    def get_object(self, *args, **kwargs):
        return DraftRegistration.load(self.kwargs.get('draft_pk'))

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body).get('schema_data', {})
            draft = DraftRegistration.load(self.kwargs.get('draft_pk'))
            draft.update_metadata(data)
            draft.save()
            log_message = list()
            for key, value in data.items():
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
    fp = BaseFileNode.load(file_id)
    wb_url = fp.generate_waterbutler_url()
    return redirect(wb_url)


def get_metadata_files(draft):
    data = draft.registration_metadata
    for q, question in get_file_questions('prereg-prize.json'):
        if not isinstance(data[q]['value'], dict):
            for i, file_info in enumerate(data[q]['extra']):
                provider = file_info['data']['provider']
                if provider != 'osfstorage':
                    raise Http404(
                        'File does not exist in OSFStorage ({}: {})'.format(
                            q, question
                        ))
                file_guid = file_info.get('fileId')
                if not file_guid:
                    node = Node.load(file_info.get('nodeId'))
                    path = file_info['data'].get('path')
                    item = BaseFileNode.resolve_class(
                        provider,
                        BaseFileNode.FILE
                    ).get_or_create(node, path)
                    file_guid = item.get_guid(create=True)._id
                    data[q]['extra'][i]['fileId'] = file_guid
                    draft.update_metadata(data)
                    draft.save()
                else:
                    item = BaseFileNode.load(file_info['data']['path'].replace('/', ''))
                if item is None:
                    raise Http404(
                        'File with guid "{}" in "{}" does not exist'.format(
                            file_guid, question
                        ))
                yield item
            continue
        for i, file_info in enumerate(data[q]['value']['uploader']['extra']):
            provider = file_info['data']['provider']
            if provider != 'osfstorage':
                raise Http404(
                    'File does not exist in OSFStorage ({}: {})'.format(
                        q, question
                    ))
            file_guid = file_info.get('fileId')
            if not file_guid:
                node = Node.load(file_info.get('nodeId'))
                path = file_info['data'].get('path')
                item = BaseFileNode.resolve_class(
                    provider,
                    BaseFileNode.FILE
                ).get_or_create(node, path)
                file_guid = item.get_guid(create=True)._id
                data[q]['value']['uploader']['extra'][i]['fileId'] = file_guid
                draft.update_metadata(data)
                draft.save()
            else:
                item = BaseFileNode.load(file_info['data']['path'].replace('/', ''))
            if item is None:
                raise Http404(
                    'File with guid "{}" in "{}" does not exist'.format(
                        file_guid, question
                    ))
            yield item


def get_file_questions(json_file):
    uploader = {
        'id': 'uploader',
        'type': 'osf-upload',
        'format': 'osf-upload-toggle'
    }
    questions = []
    schema = from_json(json_file)
    for item in schema['pages']:
        for question in item['questions']:
            if question['type'] == 'osf-upload':
                questions.append((question['qid'], question['title']))
                continue
            properties = question.get('properties')
            if properties is None:
                continue
            if uploader in properties:
                questions.append((question['qid'], question['title']))
    return questions
