import re
import json
from collections import defaultdict
from django.urls import reverse_lazy
from django.db.models import Q
from django.db import models
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, DetailView, UpdateView, CreateView, View
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from osf.models import NotificationSubscription, NotificationType, Notification, EmailTask, NotificationCampaign, OSFUser
from osf.models.notification_campaign import NotificationCampaignStatus
from django.forms.models import model_to_dict
from .forms import NotificationTypeForm, NotificationCampaignCreateForm
from mako.lexer import Lexer
from mako.parsetree import ControlLine
from string import Formatter
from osf.email import _render_email_html
from osf.email.notification_campaign import FILTER_PRESETS, filter_users


def delete_selected_notifications(selected_ids):
    NotificationSubscription.objects.filter(id__in=selected_ids).delete()

TEMPLATE_IDENTIFIER_BLACKLIST = {
    'if', 'else', 'and', 'or', 'not', 'in',
    'True', 'False', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
}

def resolve_identifiers(identifier_structure):
    structure = defaultdict(dict)
    if hasattr(identifier_structure, 'nodes') and identifier_structure.nodes:
        for node in identifier_structure.nodes:
            if isinstance(node, ControlLine) and node.keyword == 'for':
                match = re.match(r'for (\w+) in (.+):', node.text)
                if match:
                    iterator, source = match.groups()
                    structure[node.text] = {
                        'type': 'loop',
                        'iterator': iterator,
                        'source': source,
                        'children': resolve_identifiers(node)
                    }
            elif hasattr(node, 'text'):
                field_match = re.match(r"(\w+)\['(.+)'\]", node.text)
                if field_match:
                    source, field = field_match.groups()
                    structure[node.text] = {
                        'type': 'field',
                        'source': source,
                        'field': field
                    }
    return structure

def generate_mock_json(structure, list_name=None):
    item = {}
    result = {}
    for key, value in structure.items():
        # simple field
        if isinstance(value, dict) and value.get('type') == 'field':
            field_name = value['field']
            item[field_name] = f"mock_{field_name}"

        # nested loop
        elif isinstance(value, dict) and value.get('type') == 'loop':
            nested_source = value['source']
            nested_match = re.match(r"\w+\['(.+)'\]", nested_source)
            if nested_match:
                nested_field = nested_match.group(1)
                item[nested_field] = [1, 2, 3, 4]

        # top-level loop wrapper
        elif key.startswith('for '):
            match = re.match(r'for (\w+) in (.+):', key)
            if match:
                _, source = match.groups()
                # Extract final field name
                field_match = re.search(r"(\w+)\['(.+?)'\]$", source)
                if field_match:
                    field_name = field_match.group(1)
                    list_name = field_match.group(2)
                    return {field_name: generate_mock_json(value, list_name)}
                else:
                    list_name = source
                return generate_mock_json(value, list_name)
    if list_name:
        result[list_name] = [item, item, item]

    return result


def build_safe_context(template: str, subject: str) -> dict:
    templatenode = Lexer(text=template).parse()
    identifiers_location = []
    for node in templatenode.get_children():
        if hasattr(node, 'nodes'):
            identifiers_location.extend(node.nodes)

    if not identifiers_location:
        identifiers_location = templatenode.get_children()
    identifier_structure = defaultdict()
    for control_structure in identifiers_location:
        if isinstance(control_structure, ControlLine):
            identifier_structure[control_structure.text] = resolve_identifiers(control_structure)

    identifiers = [x.undeclared_identifiers() for x in identifiers_location if hasattr(x, 'undeclared_identifiers')]
    flatten_identifiers = set()
    for indentifier_set in identifiers:
        flatten_identifiers.update(indentifier_set)
    mock_json = generate_mock_json(identifier_structure)
    context = {identifier: f'mock_{identifier}' for identifier in flatten_identifiers if identifier not in TEMPLATE_IDENTIFIER_BLACKLIST}
    context.update(mock_json)

    # subject
    context.update({key: key for _, key, _, _ in Formatter().parse(subject) if key})
    return context

class NotificationsList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'notifications/notifications_list.html'
    ordering = 'id'
    permission_required = 'osf.view_notification'
    raise_exception = True
    model = Notification

    def get_queryset(self):
        qs = Notification.objects.all().order_by(self.ordering)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(subscription__notification_type__name__icontains=q) |
                Q(subscription__user__username__icontains=q) |
                Q(subscription__message_frequency__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '')
        context['q'] = q
        # append search param to pagination links
        if q:
            context['extra_query_params'] = f"&q={q}"
        else:
            context['extra_query_params'] = ''

        context['notifications'] = context['object_list']
        context['page'] = context['page_obj']
        return context

class NotificationSubscriptionsList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'notifications/notification_subscriptions_list.html'
    ordering = 'id'
    permission_required = 'osf.view_notificationsubscription'
    raise_exception = True
    model = NotificationSubscription

    def get_queryset(self):
        qs = NotificationSubscription.objects.all().order_by(self.ordering)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(notification_type__name__icontains=q) |
                Q(user__username__icontains=q) |
                Q(message_frequency__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '')
        context['q'] = q
        # append search param to pagination links
        if q:
            context['extra_query_params'] = f"&q={q}"
        else:
            context['extra_query_params'] = ''
        context['subscriptions'] = context['object_list']
        context['page'] = context['page_obj']
        return context

class EmailTasksList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'notifications/email_tasks_list.html'
    ordering = 'task_id'
    permission_required = 'osf.view_emailtask'
    raise_exception = True
    model = EmailTask

    def get_queryset(self):
        qs = EmailTask.objects.all().order_by(self.ordering)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(task_id=q) |
                Q(user__username__icontains=q) |
                Q(status=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '')
        context['q'] = q
        # append search param to pagination links
        if q:
            context['extra_query_params'] = f"&q={q}"
        else:
            context['extra_query_params'] = ''
        context['email_tasks'] = context['object_list']
        context['page'] = context['page_obj']
        return context

class NotificationTypeList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'notifications/notification_types_list.html'
    ordering = 'name'
    permission_required = 'osf.view_notificationtype'
    raise_exception = True
    model = NotificationType

    def get_queryset(self):
        qs = NotificationType.objects.all().order_by(self.ordering)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(subject__icontains=q) |
                Q(notification_interval_choices__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '')
        context['q'] = q
        # append search param to pagination links
        if q:
            context['extra_query_params'] = f"&q={q}"
        else:
            context['extra_query_params'] = ''

        context['notification_types'] = context['object_list']
        context['page'] = context['page_obj']
        return context

class NotificationTypeDisplay(PermissionRequiredMixin, DetailView):
    model = NotificationType
    template_name = 'notifications/notification_type_detail.html'
    permission_required = 'osf.view_notificationtype'
    raise_exception = True

    def get_object(self, queryset=None):
        return NotificationType.objects.get(id=self.kwargs.get('pk'))

    def get_context_data(self, *args, **kwargs):
        notification_type = self.get_object()
        notification_type_dict = model_to_dict(notification_type)
        fields = notification_type_dict.copy()
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))
        notification_type_dict['is_digest_type'] = notification_type.is_digest_type
        kwargs['notification_type'] = notification_type_dict
        kwargs['template'] = notification_type_dict.pop('template', None)
        kwargs['change_form'] = NotificationTypeForm(initial=fields)

        return kwargs

class NotificationTypePreview(PermissionRequiredMixin, DetailView):
    model = NotificationType
    template_name = 'notifications/notification_type_preview.html'
    permission_required = 'osf.view_notificationtype'
    raise_exception = True

    def get_object(self, queryset=None):
        return NotificationType.objects.get(id=self.kwargs.get('pk'))

    def get_context_data(self, *args, **kwargs):
        notification_type = self.get_object()
        raw_context = self.request.GET.get('context')
        if raw_context:
            try:
                if notification_type.is_digest_type:
                    safe_context = {'notifications': [json.loads(raw_context)]}
                else:
                    safe_context = json.loads(raw_context)

                return_context = json.loads(raw_context)
            except json.JSONDecodeError as e:
                kwargs['rendered_template'] = f"Error parsing JSON: {str(e)}"
                kwargs['context'] = raw_context
                return kwargs
        else:
            if notification_type.is_digest_type:
                inner_context = build_safe_context(notification_type.template, notification_type.subject)
                inner_template = _render_email_html(notification_type, ctx=inner_context, return_original_error=True)
                safe_context = {'notifications': [inner_template]}
                return_context = inner_context
            else:
                safe_context = build_safe_context(notification_type.template, notification_type.subject)
                return_context = safe_context

        if notification_type.is_digest_type:
            # Use user_digest template as a wrapper for digest notification preview.
            template_obj = NotificationType.objects.get(name='user_digest')
        else:
            template_obj = notification_type
        try:
            kwargs['rendered_template'] = _render_email_html(template_obj, ctx=safe_context, return_original_error=True)
        except Exception as e:
            kwargs['rendered_template'] = f"Error rendering template: {str(e)}"

        kwargs['rendered_subject'] = notification_type.subject.format(**safe_context)
        kwargs['context'] = json.dumps(return_context, indent=4)

        return kwargs

class NotificationTypeDetail(PermissionRequiredMixin, DetailView):
    model = NotificationType
    template_name = 'notifications/notification_type_detail.html'
    permission_required = 'osf.view_notificationtype'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        view = NotificationTypeDetail.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = NotificationTypeChangeForm.as_view()
        return view(request, *args, **kwargs)

class NotificationTypeChangeForm(PermissionRequiredMixin, UpdateView):
    template_name = 'institutions/detail.html'
    permission_required = 'osf.change_notificationtype'
    raise_exception = True
    model = NotificationType
    form_class = NotificationTypeForm

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('notifications:type_display', kwargs={'pk': self.kwargs.get('pk')})


class NotificationCampaignsList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'notifications/notification_campaigns_list.html'
    ordering = 'name'
    permission_required = 'osf.view_notificationcampaign'
    raise_exception = True
    model = NotificationCampaign

    def get_queryset(self):
        qs = NotificationCampaign.objects.all().order_by(self.ordering)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(status__icontains=q) |
                Q(notification_type__name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '')
        context['q'] = q
        # append search param to pagination links
        if q:
            context['extra_query_params'] = f"&q={q}"
        else:
            context['extra_query_params'] = ''

        context['notification_campaigns'] = context['object_list']
        context['page'] = context['page_obj']
        return context


class NotificationCampaignDetail(PermissionRequiredMixin, DetailView):
    model = NotificationCampaign
    template_name = 'notifications/notification_campaigns_detail.html'
    permission_required = 'osf.change_notificationcampaign'
    raise_exception = True

    def get_object(self, queryset=None):
        return NotificationCampaign.objects.get(id=self.kwargs.get('pk'))

    def get_context_data(self, *args, **kwargs):
        notification_campaign = self.get_object()
        metadata = notification_campaign.metadata or {}

        context = {
            'notification_campaign': notification_campaign,
            'display_fields': [
                ('Name', notification_campaign.name),
                ('Notification Type', notification_campaign.notification_type),
                ('Created By', notification_campaign.created_by),
                ('Status', notification_campaign.get_status_display()),
                ('Recipients', notification_campaign.recipient_count),
                ('Sent', notification_campaign.sent_count),
                ('Failed', notification_campaign.failed_count),
                ('Retries', notification_campaign.retries),
                ('Created', notification_campaign.created_at),
                ('Started', notification_campaign.started_at),
                ('Completed', notification_campaign.completed_at),
            ],
            'template': notification_campaign.notification_type.template,
            'metadata': metadata,
            'filters_json': json.dumps(notification_campaign.metadata['filters']),
            'sent_filters_json': json.dumps({
                'manual': [
                    {'field': 'notificationcampaignrecipient', 'value': notification_campaign.id, 'lookup': 'campaign'},
                    {'field': 'notificationcampaignrecipient', 'value': 'sent', 'lookup': 'status'}
                ]
            }),
            'failed_filters_json': json.dumps({
                'manual': [
                    {'field': 'notificationcampaignrecipient', 'value': notification_campaign.id, 'lookup': 'campaign'},
                    {'field': 'notificationcampaignrecipient', 'value': 'failed', 'lookup': 'status'}
                ]
            }),
            'other_metadata': {
                k: v
                for k, v in metadata.items()
                if k not in {'filters', 'context', 'execution', 'template'}
            },
        }

        if notification_campaign.status == NotificationCampaignStatus.RUNNING:
            context.update({
                'sent_percent': notification_campaign.sent_count * 100 / notification_campaign.recipient_count if notification_campaign.recipient_count else 0,
                'failed_percent': notification_campaign.failed_count * 100 / notification_campaign.recipient_count if notification_campaign.recipient_count else 0,
            })

        return context


LOOKUPS = {
    models.CharField: {
        'exact': 'Equals',
        'iexact': 'Equals (case insensitive)',
        'contains': 'Contains',
        'icontains': 'Contains (case insensitive)',
        'startswith': 'Starts with',
        'istartswith': 'Starts with (case insensitive)',
        'endswith': 'Ends with',
        'iendswith': 'Ends with (case insensitive)',
        'in': 'In',
        'isnull': 'Is empty',
    },
    models.TextField: {
        'exact': 'Equals',
        'iexact': 'Equals (case insensitive)',
        'contains': 'Contains',
        'icontains': 'Contains (case insensitive)',
        'startswith': 'Starts with',
        'istartswith': 'Starts with (case insensitive)',
        'endswith': 'Ends with',
        'iendswith': 'Ends with (case insensitive)',
        'isnull': 'Is empty',
    },
    models.IntegerField: {
        'exact': 'Equals',
        'gt': 'Greater than',
        'gte': 'Greater than or equal to',
        'lt': 'Less than',
        'lte': 'Less than or equal to',
        'in': 'In',
        'isnull': 'Is empty',
    },
    models.DateField: {
        'exact': 'On',
        'gt': 'After',
        'gte': 'On or after',
        'lt': 'Before',
        'lte': 'On or before',
        'isnull': 'Is empty',
    },
    models.DateTimeField: {
        'exact': 'On',
        'gt': 'After',
        'gte': 'On or after',
        'lt': 'Before',
        'lte': 'On or before',
        'isnull': 'Is empty',
    },
    models.BooleanField: {
        'exact': 'Is',
    },
}


class NotificationCampaignCreateView(CreateView):
    model = NotificationCampaign
    form_class = NotificationCampaignCreateForm
    template_name = 'notifications/notification_campaing_create.html'
    allowed_filters = [
        'is_active',
        'is_staff',
        'username',
        'last_login',
    ]

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        form.instance.metadata = {
            'filters': form.cleaned_data['filters'],
            'context': form.cleaned_data['context'],
            'execution': {
                'batch_size': form.cleaned_data['batch_size'],
                'max_retries': form.cleaned_data['max_retries'],
                'activity_threshold': form.cleaned_data['activity_threshold'],
            },
        }

        response = super().form_valid(form)

        messages.success(
            self.request,
            'Notification campaign created successfully.',
        )

        return response

    def get_success_url(self):
        return reverse_lazy(
            'notifications:notification_campaigns_detail',
            kwargs={'pk': self.object.pk},
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notification_types'] = NotificationType.objects.order_by('name')

        filter_fields = {}
        for field in [f for f in OSFUser._meta.get_fields() if f.name in self.allowed_filters]:
            if not field.concrete:
                continue
            if type(field) not in LOOKUPS.keys():
                continue
            filter_fields[field.name] = {
                'label': field.verbose_name,
                'type': field.get_internal_type().lower(),
                'lookups': LOOKUPS.get(type(field), {})
            }
        context['filter_fields'] = filter_fields
        context['filters'] = []
        context['predefined_filters'] = FILTER_PRESETS.keys()
        return context


class NotificationCampaignsRecipientsPreview(PermissionRequiredMixin, ListView):
    template_name = 'users/list.html'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    paginate_by = 25

    def get_queryset(self):
        filters = {}
        raw_filters = self.request.GET.get('filters', None)
        if raw_filters:
            json_filters = json.loads(raw_filters)
            if predefined := json_filters.get('predefined'):
                filters = FILTER_PRESETS.get(predefined, {})
            else:
                for item in json_filters.get('manual', []):
                    if item['lookup'] != 'in':
                        filters[f'{item["field"]}__{item["lookup"]}'] = item['value']
                    else:
                        filters[f'{item["field"]}__{item["lookup"]}'] = [value.strip() for value in item['value'].split(',')]

        return filter_users(filters)

    def get_context_data(self, **kwargs):
        users = self.get_queryset()

        page_size = self.get_paginate_by(users)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            users,
            page_size,
        )
        # append search param to pagination links
        kwargs.update({'extra_query_params': f'&filters={self.request.GET.get("filters")}'})
        return super().get_context_data(
            **kwargs,
            page=page,
            users=query_set,
            paginator=paginator,
            is_paginated=is_paginated,
        )

class StartNotificationCampaign(PermissionRequiredMixin, View):
    permission_required = 'osf.change_notificationtype'

    def post(self, request, *args, **kwargs):
        notification_campaign = get_object_or_404(
            NotificationCampaign,
            pk=kwargs['pk'],
        )

        restart_failed = request.GET.get('restart_failed') == 'true'

        notification_campaign.start(restart_failed=restart_failed)

        return redirect(
            'notifications:notification_campaigns_detail',
            pk=notification_campaign.pk,
        )
