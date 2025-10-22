from django.contrib import admin, messages
from django.urls import re_path, reverse, path
from django.template.response import TemplateResponse
from django_extensions.admin import ForeignKeyAutocompleteAdmin
from django.contrib.auth.models import Group
from django.db.models import Q, Count
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.utils.html import format_html
from django.shortcuts import get_object_or_404
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from django.contrib.admin import SimpleListFilter
import waffle

from osf.external.spam.tasks import reclassify_domain_references
from osf.models import OSFUser, Node, NotableDomain, NodeLicense, NotificationType, NotificationSubscription, EmailTask
from osf.models.notification_type import get_default_frequency_choices
from osf.models.notable_domain import DomainReference


def list_displayable_fields(cls):
    return [x.name for x in cls._meta.fields if x.editable and not x.is_relation and not x.primary_key]

class NodeAdmin(ForeignKeyAutocompleteAdmin):
    fields = list_displayable_fields(Node)

class OSFUserAdmin(admin.ModelAdmin):
    fields = ['groups', 'user_permissions'] + list_displayable_fields(OSFUser)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Restricts preprint/node django groups from showing up in the user's groups list in the admin app
        """
        if db_field.name == 'groups':
            kwargs['queryset'] = Group.objects.exclude(Q(name__startswith='preprint_') | Q(name__startswith='node_') | Q(name__startswith='collections_'))
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_related(self, request, form, formsets, change):
        """
        Since m2m fields overridden with new form data in admin app, preprint groups/node groups (which are now excluded from being selections)
        are removed.  Manually re-adds preprint/node groups after adding new groups in form.
        """
        groups_to_preserve = list(form.instance.groups.filter(Q(name__startswith='preprint_') | Q(name__startswith='node_') | Q(name__startswith='collections_')))
        super().save_related(request, form, formsets, change)
        if 'groups' in form.cleaned_data:
            for group in groups_to_preserve:
                form.instance.groups.add(group)


class LicenseAdmin(admin.ModelAdmin):
    fields = list_displayable_fields(NodeLicense)


class NotableDomainAdmin(admin.ModelAdmin):
    fields = list_displayable_fields(NotableDomain)
    ordering = ('-id',)
    list_display = ('domain', 'note', 'number_of_references')
    list_filter = ('note',)
    search_fields = ('domain',)
    actions = ['make_ignored', 'make_excluded']

    @admin.display(ordering='number_of_references')
    def number_of_references(self, obj):
        return obj.number_of_references

    @admin.action(description='Mark selected as IGNORED')
    def make_ignored(self, request, queryset):
        signatures = []
        target_note = 3  # IGNORED
        for obj in queryset:
            signatures.append({
                'notable_domain_id': obj.pk,
                'current_note': target_note,
                'previous_note': obj.note
            })
        queryset.update(note=target_note)
        for sig in signatures:
            reclassify_domain_references.apply_async(kwargs=sig)

    @admin.action(description='Mark selected as EXCLUDED')
    def make_excluded(self, request, queryset):
        signatures = []
        target_note = 0  # EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT
        for obj in queryset:
            signatures.append({
                'notable_domain_id': obj.pk,
                'current_note': target_note,
                'previous_note': obj.note
            })
        queryset.update(note=target_note)
        for sig in signatures:
            reclassify_domain_references.apply_async(kwargs=sig)

    def get_urls(self):
        urls = super().get_urls()
        return [
            re_path(
                r'^bulkadd/$',
                self.admin_site.admin_view(self.bulk_add_view),
                name='osf_notabledomain_bulkadd',
            ),
            *urls,
        ]

    def bulk_add_view(self, request):
        if request.method == 'GET':

            context = {
                **self.admin_site.each_context(request),
                'note_choices': list(NotableDomain.Note),
            }
            return TemplateResponse(request, 'admin/osf/notabledomain/bulkadd.html', context)

        if request.method == 'POST':
            domains = filter(
                None,  # remove empty lines
                request.POST['notable_email_domains'].split('\n'),
            )
            num_added = self._bulk_add(domains, request.POST['note'])
            self.message_user(
                request,
                f'Success! {num_added} notable email domains added!',
                messages.SUCCESS,
            )
            return HttpResponseRedirect(reverse('admin:osf_notabledomain_changelist'))

    def _bulk_add(self, domain_names, note):
        num_added = 0
        for domain_name in domain_names:
            domain_name = domain_name.strip().lower()
            if domain_name:
                num_added += 1
                NotableDomain.objects.update_or_create(
                    domain=domain_name,
                    defaults={
                        'note': note,
                    },
                )
        return num_added

    def change_view(self, request, object_id, form_url='', extra_context=None):
        references = DomainReference.objects.filter(domain_id=object_id)
        return self.changeform_view(request, object_id, form_url, {'references': references})

    def get_queryset(self, request):
        qs = super().get_queryset(request).annotate(number_of_references=Count('domainreference'))
        return qs


class _ManygroupWaffleFlagAdmin(waffle.admin.FlagAdmin):
    '''customized `waffle.admin.FlagAdmin` to support many groups

    waffle assumes "there are likely not that many" groups [0],
    but in osf there are, in fact, that many groups.

    [0]: https://github.com/jazzband/django-waffle/commit/bf36c19ee03baf1c5850ffe0b284900a5c416f53
    '''
    raw_id_fields = (*waffle.admin.FlagAdmin.raw_id_fields, 'groups')


class NotificationTypeAdminForm(forms.ModelForm):
    default_intervals = forms.MultipleChoiceField(
        choices=[(c, c) for c in get_default_frequency_choices()],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Default Intervals'
    )

    custom_intervals = SimpleArrayField(
        base_field=forms.CharField(),
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        label='Custom Intervals (comma-separated)'
    )

    class Meta:
        model = NotificationType
        exclude = ['notification_interval_choices']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill existing values
        if self.instance and self.instance.notification_interval_choices:
            defaults = get_default_frequency_choices()
            existing = self.instance.notification_interval_choices
            self.fields['default_intervals'].initial = [v for v in existing if v in defaults]
            self.fields['custom_intervals'].initial = [v for v in existing if v not in defaults]

    def save(self, commit=True):
        # Assign combined intervals
        default_intervals = self.cleaned_data.get('default_intervals') or []
        custom_intervals = self.cleaned_data.get('custom_intervals') or []
        combined = list(default_intervals + custom_intervals)

        self.instance.notification_interval_choices = combined

        return super().save(commit=commit)


class NotificationIntervalFilter(SimpleListFilter):
    title = 'Notification Interval'
    parameter_name = 'notification_interval'

    def lookups(self, request, model_admin):
        default_choices = [(choice, choice) for choice in get_default_frequency_choices()]
        custom_choices_list = [
            (choice, choice)
            for choice_list in NotificationType.objects.values_list('notification_interval_choices', flat=True).distinct()
            for choice in choice_list
            if choice not in get_default_frequency_choices()
        ]
        return default_choices + list(set(custom_choices_list))

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(notification_interval_choices__contains=[self.value()])
        return queryset

class NotificationTypeAdmin(admin.ModelAdmin):
    form = NotificationTypeAdminForm
    list_display = ('name', 'object_content_type', 'notification_interval_choices', 'preview_button')
    list_filter = (NotificationIntervalFilter,)
    search_fields = ('name',)

    def preview_button(self, obj):
        return format_html(
            '<a class="button" target="_blank" href="{}">Preview</a>',
            f'{obj.id}/preview/'
        )

    def get_urls(self):
        custom_urls = [
            path(
                '<int:pk>/preview/',
                self.admin_site.admin_view(self._preview_notification_template_view),
                name='notificationtype_preview',
            ),
        ]
        return custom_urls + super().get_urls()

    def _preview_notification_template_view(self, request, pk):
        obj = get_object_or_404(NotificationType, pk=pk)
        return HttpResponse('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Template Preview</title>
                <style>
                    html {
                        padding: 40px;
                    }
                    body {
                        font-family: sans-serif;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }
                    h1, h2 {
                        color: #333;
                    }
                    .code-box {
                    justify-content: center;
                    background-color: #1e1e1e;
                    color: #dcdcdc;
                    border: 1px solid #444;
                    padding: 15px;
                    overflow: auto;
                    white-space: pre-wrap;
                    word-break: break-word;
                    max-height: 80vh;
                    font-family: monospace;
                    border-radius: 8px;
                    resize: both;
                }
                </style>
            </head>''' + f'''
            <body>
                <div class="container">
                    <div class="content">
                        <h1>Template Preview for {obj.name}</h1>
                        <p><strong>Object Content Type:</strong> {obj.object_content_type}</p>
                        <p><strong>Notification Intervals:</strong> {', '.join(obj.notification_interval_choices)}</p>
                        <h2>Subject:</h2>
                        <p>{obj.subject}</p>

                        <h2>Template:</h2>
                        <div class="code-box">{obj.template}</div>
                    </div>
                </div>
            </body>
            </html>''', content_type='text/html')


class NotificationSubscriptionForm(forms.ModelForm):
    class Meta:
        model = NotificationSubscription
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        notification_type_id = (
            self.data.get('notification_type') or
            getattr(self.instance.notification_type, 'id', None)
        )

        if notification_type_id:
            try:
                nt = NotificationType.objects.get(pk=notification_type_id)
                choices = [(x, x) for x in nt.notification_interval_choices]
            except NotificationType.DoesNotExist:
                choices = []
        else:
            choices = []

        self.fields['message_frequency'] = forms.ChoiceField(
            choices=choices,
            required=False
        )

class NotificationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'message_frequency', 'subscribed_object', 'preview_button')
    form = NotificationSubscriptionForm

    class Media:
        js = ['admin/notification_subscription.js']

    def preview_button(self, obj):
        if obj.notification_type:
            url = reverse(
                'admin:notificationtype_preview',
                args=[obj.notification_type.id]
            )
            return format_html(
                '<a class="button" target="_blank" href="{}">Preview</a>',
                url
            )
        return format_html(
            '<a class="button">Missing Notification Type!</a>',
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'get-intervals/<int:pk>/',
                self.admin_site.admin_view(self.get_intervals),
                name='get_notification_intervals'
            ),
        ]
        return custom_urls + urls

    def get_intervals(self, request, pk):
        try:
            nt = NotificationType.objects.get(pk=pk)
            return JsonResponse({'intervals': nt.notification_interval_choices})
        except NotificationType.DoesNotExist:
            return JsonResponse({'intervals': []})


@admin.register(EmailTask)
class EmailTaskAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'user', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('task_id', 'user__email')

admin.site.register(OSFUser, OSFUserAdmin)
admin.site.register(Node, NodeAdmin)
admin.site.register(NotableDomain, NotableDomainAdmin)
admin.site.register(NodeLicense, LicenseAdmin)
admin.site.register(NotificationType, NotificationTypeAdmin)
admin.site.register(NotificationSubscription, NotificationSubscriptionAdmin)

# waffle admins, with Flag admin override
admin.site.register(waffle.models.Flag, _ManygroupWaffleFlagAdmin)
admin.site.register(waffle.models.Sample, waffle.admin.SampleAdmin)
admin.site.register(waffle.models.Switch, waffle.admin.SwitchAdmin)
