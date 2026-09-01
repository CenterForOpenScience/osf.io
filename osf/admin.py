from collections import defaultdict
from datetime import timedelta

from django.contrib import admin, messages
from django.urls import re_path, reverse, path
from django.template.response import TemplateResponse
from django_extensions.admin import ForeignKeyAutocompleteAdmin
from django.contrib.auth.models import Group
from django.db.models import Q, Count, Sum, F, Min, Max, Case, When, Value, IntegerField
from django.db.models.functions import Trunc
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.html import format_html
from django.shortcuts import get_object_or_404
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from django.contrib.admin import SimpleListFilter
import waffle

from rangefilter.filters import DateTimeRangeFilterBuilder

from osf.external.spam.tasks import reclassify_domain_references
from osf.models import (
    OSFUser,
    Node,
    NotableDomain,
    NodeLicense,
    NotificationType,
    NotificationSubscription,
    EmailTask,
    Notification,
    DownloadEvent
)
from osf.models import AbstractNode, Preprint, Guid
from osf.models.notification_type import get_default_frequency_choices
from osf.models.notable_domain import DomainReference


DASHBOARD_GROUP_NAME = 'download_telemetry'


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
    search_fields = ('notification_type__name', 'user__username')

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
    search_fields = ('task_id', 'user__username')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type_name', 'sent', 'fake_sent')
    list_filter = ('sent',)
    search_fields = ('subscription__notification_type__name', 'subscription__user__username')
    list_per_page = 50

    def notification_type_name(self, obj):
        try:
            return obj.subscription.notification_type.name
        except Exception:
            return '(notification type)'
    notification_type_name.short_description = 'Notification Type'

    def user(self, obj):
        try:
            return obj.subscription.user.username
        except Exception:
            return '(username)'
    user.short_description = 'User'


# A zip that didn't complete failed through no fault of the user whenever it ended on an
# error status -- a 4xx (e.g. an add-on provider returning 404 for the resource) or a 5xx
# (the server buckled). A cancel is the other case: completed=False at a success status
# (200/302), because the headers already went out and the client aborted mid-stream. This
# threshold is what separates a real failure from a cancel.
DOWNLOAD_FAILURE_MIN_STATUS = 400


class DownloadOutcomeFilter(SimpleListFilter):
    """Filter zips by how they ended: completed, cancelled mid-stream, or failed."""

    title = 'download outcome'
    parameter_name = 'outcome'

    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    FAILED = 'failed'

    def lookups(self, request, model_admin):
        return [
            (self.COMPLETED, 'Completed'),
            (self.CANCELLED, 'Cancelled mid-download'),
            (self.FAILED, 'Failed (server or provider error)'),
        ]

    def queryset(self, request, queryset):
        if self.value() == self.COMPLETED:
            return queryset.filter(zip_completed=True)
        if self.value() == self.FAILED:
            return queryset.filter(
                zip_completed=False, status_code__gte=DOWNLOAD_FAILURE_MIN_STATUS)
        if self.value() == self.CANCELLED:
            return queryset.filter(zip_completed=False).exclude(
                status_code__gte=DOWNLOAD_FAILURE_MIN_STATUS)
        return queryset


class InputFilter(SimpleListFilter):
    """A sidebar filter that takes a free-text value instead of a fixed list of choices.

    Django's list filters render a set of links; project and user are far too
    high-cardinality for that. This renders a text box (see ``admin/input_filter.html``)
    and hands the typed value to :meth:`queryset`. Subclasses set ``parameter_name`` /
    ``title`` and implement ``queryset``.
    """
    template = 'admin/input_filter.html'

    def lookups(self, request, model_admin):
        # SimpleListFilter hides itself unless lookups() is non-empty; the value is
        # unused because choices() is overridden below.
        return ((),)

    def choices(self, changelist):
        # keep every other active filter/search param when this box is submitted, so
        # typing a project doesn't wipe the date range or an existing user filter
        all_choice = next(super().choices(changelist))
        all_choice['query_parts'] = [
            (key, value)
            for key, value in changelist.get_filters_params().items()
            if key != self.parameter_name
        ]
        yield all_choice


class ProjectGuidFilter(InputFilter):
    """Scope the dashboard to a single project/preprint by its guid."""

    parameter_name = 'project_guid'
    title = 'project guid'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(resource_guid=value.strip())
        return queryset


class DownloadUserFilter(InputFilter):
    """Scope the dashboard to a single user, matched by email (username) or user guid."""

    parameter_name = 'download_user'
    title = 'user (email or guid)'

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            term = value.strip()
            return queryset.filter(
                Q(user__username__iexact=term) | Q(user__guids___id=term)
            )
        return queryset


@admin.register(DownloadEvent)
class DownloadEventsView(admin.ModelAdmin):
    change_list_template = 'download_events/download_events.html'
    list_display = (
        'resource_guid',
        'user_display',
        'download_type',
        'outcome',
        'zip_completed',
        'status_code',
        'path',
        'size',
        'storage_provider',
        'user_region',
        'storage_region',
        'ip',
        'source_area',
        'channel_display',
        'user_agent_display',
        'created'
    )
    list_filter = (
        (
            'created',
            DateTimeRangeFilterBuilder(
                title='date and time (UTC)',
            ),
        ),
        ProjectGuidFilter,
        DownloadUserFilter,
        'download_type',
        'download_channel',
        DownloadOutcomeFilter,
        'zip_completed',
        'storage_provider',
    )
    ordering = ('-created',)
    search_fields = (
        'user__username',
        'user__fullname',
        'user__guids___id',
        'resource_guid',
        'ip',
        'path',
        'storage_provider',
        'user_region',
        'storage_region',
        'source_area',
        'user_agent'
    )
    search_help_text = 'Search by username, full name, user or node guid, ip, path, storage provider, user or storage region, source area, user agent.'

    def get_queryset(self, request):
        """Annotate an outcome rank so the computed Outcome column is sortable.

        The rank mirrors :meth:`outcome` exactly. It's just an ordering key — it doesn't
        change what rows are returned, so the table and the dashboard aggregates are
        unaffected.
        """
        return super().get_queryset(request).annotate(
            _outcome_rank=Case(
                When(zip_completed=True, then=Value(0)),  # Completed
                When(
                    zip_completed=False,
                    status_code__gte=DOWNLOAD_FAILURE_MIN_STATUS,
                    then=Value(2),  # Failed
                ),
                When(zip_completed=False, then=Value(1)),  # Cancelled
                default=Value(3),  # single files have no outcome ('—')
                output_field=IntegerField(),
            )
        )

    @admin.display(description='User', ordering='user__username')
    def user_display(self, obj):
        """Sort the User column by the username (email) rather than the raw FK id."""
        return obj.user or '—'

    @admin.display(description='Channel', ordering='download_channel')
    def channel_display(self, obj):
        """Human-readable frontend/api/other. Blank ('—') for rows recorded before the
        field existed and for zip downloads whose channel couldn't be resolved."""
        return obj.get_download_channel_display() if obj.download_channel else '—'

    @admin.display(description='User agent', ordering='user_agent')
    def user_agent_display(self, obj):
        """Truncated in the table so it doesn't dominate the row; the full value is still
        searchable and shows on the record's detail view."""
        if not obj.user_agent:
            return '—'
        return obj.user_agent if len(obj.user_agent) <= 80 else obj.user_agent[:79] + '…'

    @admin.display(description='Outcome', ordering='_outcome_rank')
    def outcome(self, obj):
        """Human-readable end state. Single files have no outcome — they're recorded at the
        redirect before any bytes move, so they never report completion."""
        if obj.zip_completed is None:
            return '—'
        if obj.zip_completed:
            return 'Completed'
        if obj.status_code and obj.status_code >= DOWNLOAD_FAILURE_MIN_STATUS:
            return 'Failed'
        return 'Cancelled'

    @admin.display(description='Size (GB)', ordering=F('size_bytes').desc(nulls_last=True))
    def size(self, obj):
        """`size_bytes` is null when we could not determine it — that is not zero.

        Sorting puts those last rather than letting Postgres float them to the top.
        """
        if obj.size_bytes is None:
            return '—'
        return f'{self._to_gb(obj.size_bytes)}'

    def changelist_view(self, request, extra_context=None):
        for query_string in request.GET:
            # when at least one of the "created" filters is set, don't override the filter values
            if query_string.startswith('created__range'):
                break
        else:
            # by default, when the page is initially loaded or "created" filter is reset
            # show only events within the last hour
            request.GET._mutable = True
            last_hour_datetime = timezone.now() - timedelta(hours=1)
            request.GET['created__range__gte_0'] = last_hour_datetime.date().strftime('%Y-%m-%d')
            request.GET['created__range__gte_1'] = last_hour_datetime.time().strftime('%H:%M:%S')

        if extra_context is None:
            extra_context = {}
        changelist = self.get_changelist_instance(request)
        extra_context['download_events_dashboard'] = self.get_dashboard_data(changelist.get_queryset(request))
        extra_context['download_events_active_filters'] = self._active_filters(request)
        return super().changelist_view(request, extra_context=extra_context)

    # query-string param -> human label, for the "applied filters" banner above the charts
    FILTER_LABELS = (
        ('q', 'Search'),
        ('project_guid', 'Project'),
        ('download_user', 'User'),
        ('download_type', 'Download type'),
        ('outcome', 'Outcome'),
        ('zip_completed__exact', 'Zip completed'),
        ('storage_provider', 'Storage provider'),
    )

    def _active_filters(self, request):
        """The filters/search currently in effect, as ``[{'label', 'value'}]``, so the
        dashboard can show at a glance what its numbers are scoped to.

        Purely presentational — it reads the same query string the changelist already
        filtered on; it never changes what's queried.
        """
        params = request.GET
        active = []

        # the date range arrives in date+time halves; recombine them into one readable line
        date_from = ' '.join(
            part for part in (params.get('created__range__gte_0'), params.get('created__range__gte_1')) if part
        )
        date_to = ' '.join(
            part for part in (params.get('created__range__lte_0'), params.get('created__range__lte_1')) if part
        )
        if date_from or date_to:
            active.append({'label': 'Date (UTC)', 'value': f"{date_from or '…'} → {date_to or 'now'}"})

        for param, label in self.FILTER_LABELS:
            value = params.get(param)
            if value:
                active.append({'label': label, 'value': value})
        return active

    def _in_dashboard_group(self, request):
        """Membership in the allow-list group is the only key to this page.

        Deliberately not falling back to ``super()``/``has_perm``: ``ModelBackend``
        answers True to every permission check for a superuser, so anything that
        consults it would let every superuser in — the opposite of what this
        dashboard is for.
        """
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return False
        return user.groups.filter(name=DASHBOARD_GROUP_NAME).exists()

    def has_module_permission(self, request, obj=None):
        """Keeps the model off the admin index for everyone else."""
        return self._in_dashboard_group(request)

    def has_view_permission(self, request, obj=None):
        """What ``changelist_view`` actually enforces — the real gate.

        ``has_module_permission`` alone only hides the link; the page itself stays
        reachable by URL without this.
        """
        return self._in_dashboard_group(request)

    # Append-only telemetry: nothing is editable through the admin, by anyone.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # blank/null region, provider or user region all mean "we could not tell"
    UNKNOWN_REGION_LABEL = 'Unknown'
    # 1 TB = 1024 GB. GB stays the primary unit; TB is only shown once a figure is
    # genuinely terabyte-scale, so small numbers aren't cluttered with "(0.0 TB)".
    GB_PER_TB = 1024

    def _sum_bytes(self, queryset):
        return queryset.aggregate(total_bytes=Sum('size_bytes'))['total_bytes'] or 0

    def _to_gb(self, total_bytes):
        return round((total_bytes or 0) / (1024**3), 2)

    def _tb_suffix(self, gb):
        """A parenthetical TB reading for terabyte-scale figures, e.g. ' (1.21 TB)'.

        Empty below 1 TB — GB is the primary unit and we don't want '(0.0 TB)' hanging
        off every small number.
        """
        if not gb or gb < self.GB_PER_TB:
            return ''
        return f' ({round(gb / self.GB_PER_TB, 2)} TB)'

    def _percent(self, part, whole):
        """Empty ranges are normal — the default window is the last hour."""
        if not whole:
            return 0.0
        return round(part * 100 / whole, 2)

    def get_dashboard_data(self, queryset):
        file_queryset = queryset.filter(download_type=DownloadEvent.FILE)
        zip_queryset = queryset.exclude(download_type=DownloadEvent.FILE)
        total_file_downloads = file_queryset.count()
        total_zip_downloads = zip_queryset.count()
        total_bytes = self._sum_bytes(queryset)

        total_downloads = queryset.count()
        total_file_gb = self._to_gb(self._sum_bytes(file_queryset))
        total_zip_gb = self._to_gb(self._sum_bytes(zip_queryset))
        time_series = self._build_time_series(queryset)
        # each breakdown returns the ranked *known* regions plus, separately, the
        # "Unknown" bucket — so a large Unknown doesn't crowd real regions off the chart
        storage_regions, storage_regions_unknown = self._build_region_breakdown(queryset, 'storage_region')
        user_regions, user_regions_unknown = self._build_region_breakdown(queryset, 'user_region')
        # downloads and GB grouped by where the bytes came from (osfstorage vs addons)
        storage_providers, storage_providers_unknown = self._build_region_breakdown(queryset, 'storage_provider')

        # Zip outcomes. Single files are recorded before any bytes move, so they have no
        # outcome and are left out of this breakdown entirely.
        completed_zips = zip_queryset.filter(zip_completed=True).count()
        failed_zips = zip_queryset.filter(
            zip_completed=False, status_code__gte=DOWNLOAD_FAILURE_MIN_STATUS).count()
        incomplete_zips = zip_queryset.filter(zip_completed=False).count()
        zip_outcomes = {
            'completed': completed_zips,
            # everything that didn't complete and wasn't a server failure is a user cancel
            'cancelled': incomplete_zips - failed_zips,
            'failed': failed_zips,
        }

        total_gb = self._to_gb(total_bytes)
        split = {
            'file': {
                'count': total_file_downloads,
                'gb': total_file_gb,
                'gb_tb_suffix': self._tb_suffix(total_file_gb),
                'count_percent': self._percent(total_file_downloads, total_downloads),
                'gb_percent': self._percent(total_file_gb, total_gb),
            },
            'zip': {
                'count': total_zip_downloads,
                'gb': total_zip_gb,
                'gb_tb_suffix': self._tb_suffix(total_zip_gb),
                'count_percent': self._percent(total_zip_downloads, total_downloads),
                'gb_percent': self._percent(total_zip_gb, total_gb),
            },
        }

        return {
            'summary': {
                'total_downloads': total_downloads,
                'total_gb': total_gb,
                'total_gb_tb_suffix': self._tb_suffix(total_gb),
                'unique_users': queryset.exclude(user_id__isnull=True).values('user_id').distinct().count(),
                'failed_zips': failed_zips,
            },
            'split': split,
            'zip_outcomes': zip_outcomes,
            'time_series': time_series,
            'storage_regions': storage_regions,
            'storage_regions_unknown': storage_regions_unknown,
            'storage_providers': storage_providers,
            'storage_providers_unknown': storage_providers_unknown,
            'user_regions': user_regions,
            'user_regions_unknown': user_regions_unknown,
            'channels': self._build_channel_breakdown(queryset),
            'top_projects': self._build_top_resource_breakdown(queryset),
            'top_users': self._build_top_user_breakdown(queryset),
        }

    EMPTY_TIME_SERIES = {'labels': [], 'file': [], 'zip': []}

    def _build_time_series(self, queryset):
        """Bucketed GB over time, aggregated in the database.

        The range can cover millions of rows once the announcement lands, so the
        bucketing is a GROUP BY rather than a pass over every event in Python.
        """
        bounds = queryset.aggregate(start=Min('created'), end=Max('created'))
        start, end = bounds['start'], bounds['end']
        if start is None:
            return dict(self.EMPTY_TIME_SERIES)

        bucket_size = self._get_bucket_size(start, end)
        step = self._get_bucket_step(bucket_size)

        rows = queryset.annotate(
            bucket=Trunc('created', self._get_trunc_kind(bucket_size))
        ).values('bucket', 'download_type').annotate(
            total_bytes=Sum('size_bytes'),
        )

        totals = defaultdict(lambda: {'file': 0.0, 'zip': 0.0})
        for row in rows:
            key = self._floor_to_bucket(row['bucket'], bucket_size)
            side = 'file' if row['download_type'] == DownloadEvent.FILE else 'zip'
            totals[key][side] += (row['total_bytes'] or 0) / (1024**3)

        # walk the whole span so gaps render as zero rather than closing up
        buckets = []
        current = self._floor_to_bucket(start, bucket_size)
        last = self._floor_to_bucket(end, bucket_size)
        while current <= last:
            buckets.append(current)
            current += step

        return {
            'labels': [self._format_bucket_label(bucket, bucket_size) for bucket in buckets],
            'file': [round(totals[bucket]['file'], 2) for bucket in buckets],
            'zip': [round(totals[bucket]['zip'], 2) for bucket in buckets],
        }

    def _get_trunc_kind(self, bucket_size):
        """15-minute buckets have no Trunc equivalent, so truncate to the hour and
        let `_floor_to_bucket` split it down."""
        return {
            '15m': 'minute',
            '1h': 'hour',
            '1d': 'day',
            '1w': 'week',
        }[bucket_size]

    def _get_bucket_size(self, start, end):
        delta = end - start
        if delta <= timedelta(hours=2):
            return '15m'
        if delta <= timedelta(hours=24):
            return '1h'
        if delta <= timedelta(days=14):
            return '1d'
        return '1w'

    def _get_bucket_step(self, bucket_size):
        if bucket_size == '15m':
            return timedelta(minutes=15)
        if bucket_size == '1h':
            return timedelta(hours=1)
        if bucket_size == '1d':
            return timedelta(days=1)
        return timedelta(days=7)

    def _floor_to_bucket(self, value, bucket_size):
        """Snap to the start of the containing bucket.

        The result is used as a dict key, so it has to land on exactly the same
        instant whether it came from an event or from walking the axis — every
        branch zeroes everything below its own resolution.
        """
        if bucket_size == '15m':
            return value.replace(minute=(value.minute // 15) * 15, second=0, microsecond=0)
        if bucket_size == '1h':
            return value.replace(minute=0, second=0, microsecond=0)
        midnight = value.replace(hour=0, minute=0, second=0, microsecond=0)
        if bucket_size == '1d':
            return midnight
        return midnight - timedelta(days=value.weekday())

    def _format_bucket_label(self, value, bucket_size):
        if bucket_size == '15m':
            return value.strftime('%H:%M')
        if bucket_size == '1h':
            return value.strftime('%Y-%m-%d %H:%M')
        if bucket_size == '1d':
            return value.strftime('%Y-%m-%d')
        return value.strftime('%Y-%m-%d')

    def _build_region_breakdown(self, queryset, field_name):
        """Grouped in the database — the range can cover millions of rows.

        `downloads` is the total request count; `file_count` and `zip_count` split it by
        request type (a zip is either a folder or a whole-project zip), so file + zip always
        equals the total.

        Returns ``(known_regions, unknown)``. "Unknown" (blank/null — we couldn't tell) is
        pulled out of the ranked list and returned on its own, so a large Unknown bucket
        doesn't crowd the real regions off the chart. The percentages scale to the largest
        *known* region, so the country bars stay readable no matter how big Unknown is.
        ``unknown`` is ``None`` when every row resolved to a real region.
        """
        rows = queryset.values(field_name).annotate(
            downloads=Count('id'),
            total_bytes=Sum('size_bytes'),
            file_count=Count('id', filter=Q(download_type=DownloadEvent.FILE)),
            zip_count=Count('id', filter=~Q(download_type=DownloadEvent.FILE)),
        )

        breakdown = defaultdict(lambda: {'downloads': 0, 'gb': 0.0, 'file_count': 0, 'zip_count': 0})
        for row in rows:
            # blank and null both mean "we could not tell", so they fold together
            region_name = (row[field_name] or self.UNKNOWN_REGION_LABEL).strip() or self.UNKNOWN_REGION_LABEL
            breakdown[region_name]['downloads'] += row['downloads']
            breakdown[region_name]['gb'] += (row['total_bytes'] or 0) / (1024**3)
            breakdown[region_name]['file_count'] += row['file_count']
            breakdown[region_name]['zip_count'] += row['zip_count']

        unknown_data = breakdown.pop(self.UNKNOWN_REGION_LABEL, None)

        # gb descending, then name ascending so the order is deterministic when GB ties
        # (and never depends on the incoming queryset's row order)
        ordered = sorted(breakdown.items(), key=lambda item: (-item[1]['gb'], item[0]))[:10]
        max_gb = max((data['gb'] for _, data in ordered), default=0)
        max_downloads = max((data['downloads'] for _, data in ordered), default=0)
        known_regions = [
            {
                'name': name,
                'downloads': data['downloads'],
                'file_count': data['file_count'],
                'zip_count': data['zip_count'],
                'gb': round(data['gb'], 2),
                'gb_percent': self._percent(data['gb'], max_gb),
                'download_percent': self._percent(data['downloads'], max_downloads),
            }
            for name, data in ordered
        ]
        unknown = None
        if unknown_data:
            unknown = {
                'name': self.UNKNOWN_REGION_LABEL,
                'downloads': unknown_data['downloads'],
                'file_count': unknown_data['file_count'],
                'zip_count': unknown_data['zip_count'],
                'gb': round(unknown_data['gb'], 2),
            }
        return known_regions, unknown

    def _build_channel_breakdown(self, queryset):
        """Downloads + GB grouped by channel (frontend / api / other) — the explicit split
        the User-Agent alone could never give us. Rows with no channel (recorded before the
        field, or zips whose channel couldn't be resolved) are reported as 'Unknown'."""
        rows = queryset.values('download_channel').annotate(
            downloads=Count('id'),
            total_bytes=Sum('size_bytes'),
        )
        labels = dict(DownloadEvent.DOWNLOAD_CHANNELS)
        # Fold by channel in Python: a pre-existing annotation on the queryset (e.g. the
        # sort's _outcome_rank) can leak into the GROUP BY and split a channel across rows,
        # so sum them back together — same reason _build_region_breakdown folds.
        folded = defaultdict(lambda: {'downloads': 0, 'bytes': 0})
        for row in rows:
            channel = row['download_channel'] or ''
            folded[channel]['downloads'] += row['downloads']
            folded[channel]['bytes'] += (row['total_bytes'] or 0)

        # frontend, api, other, then unknown last — a stable, meaningful order
        rank = {DownloadEvent.FRONTEND: 0, DownloadEvent.API: 1, DownloadEvent.OTHER: 2, '': 3}
        breakdown = [
            {
                'name': labels.get(channel, 'Unknown') if channel else 'Unknown',
                'channel': channel,
                'downloads': data['downloads'],
                'gb': self._to_gb(data['bytes']),
            }
            for channel, data in folded.items()
        ]
        breakdown.sort(key=lambda item: (rank.get(item['channel'], 4), item['name']))
        return breakdown

    def _build_top_resource_breakdown(self, queryset):
        rows = queryset.exclude(resource_guid='').values('resource_guid').annotate(
            gb_bytes=Sum('size_bytes'),
            downloads=Count('id'),
        ).order_by(F('gb_bytes').desc(nulls_last=True), '-downloads')[:10]
        rows = list(rows)

        # one query for all ten, rather than one per row
        guids = [row['resource_guid'] for row in rows]
        titles = dict(
            AbstractNode.objects.filter(guids___id__in=guids).values_list('guids___id', 'title')
        )
        # preprints aren't nodes, and a preprint guid can be versioned (e.g. abcde_v1), which
        # the node query above never matches. Resolve whatever's left through the guid — at
        # most ten lookups, since this is a top-ten table.
        for guid in guids:
            if guid not in titles:
                referent, _ = Guid.load_referent(guid)
                if isinstance(referent, Preprint) and referent.title:
                    titles[guid] = referent.title
        return [
            {
                # a deleted project keeps its title, but fall back to the bare guid so
                # the row still says something if it ever fails to resolve
                'name': (
                    f'{titles[row["resource_guid"]]} ({row["resource_guid"]})'
                    if row['resource_guid'] in titles
                    else row['resource_guid']
                ),
                'downloads': row['downloads'],
                'gb': self._to_gb(row['gb_bytes']),
            }
            for row in rows
        ]

    def _build_top_user_breakdown(self, queryset):
        rows = queryset.exclude(user__isnull=True).values('user__username', 'user__fullname').annotate(
            gb_bytes=Sum('size_bytes'),
            downloads=Count('id'),
        ).order_by(F('gb_bytes').desc(nulls_last=True), '-downloads')[:10]
        return [
            {
                'name': row['user__fullname'] or row['user__username'] or 'Unknown user',
                'downloads': row['downloads'],
                'gb': self._to_gb(row['gb_bytes']),
            }
            for row in rows
        ]


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
