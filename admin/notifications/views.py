from django.urls import reverse_lazy
from django.db.models import Q
from osf.models import NotificationSubscription, NotificationType, Notification, EmailTask
from django.views.generic import ListView, DetailView, UpdateView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.forms.models import model_to_dict
from .forms import NotificationTypeForm
from osf.email import _render_email_html
import json
from collections import defaultdict
from mako.lexer import Lexer
from mako.parsetree import ControlLine
import re

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


def build_safe_context(template: str) -> dict:
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
            if notification_type.is_digest_type:
                safe_context = {'notifications': [json.loads(raw_context)]}
            else:
                safe_context = json.loads(raw_context)

            return_context = json.loads(raw_context)
        else:
            if notification_type.is_digest_type:
                inner_context = build_safe_context(notification_type.template)
                inner_template = _render_email_html(notification_type, ctx=inner_context, return_original_error=True)
                safe_context = {'notifications': [inner_template]}
                return_context = inner_context
            else:
                safe_context = build_safe_context(notification_type.template)
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
