from datetime import timedelta

from django.apps import apps as global_apps
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, Permission
from django.test import RequestFactory
from django.utils import timezone

from osf.admin import (
    DASHBOARD_GROUP_NAME,
    DownloadEventsView,
    ProjectGuidFilter,
    DownloadUserFilter,
)
from osf.models import DownloadEvent
from osf_tests.factories import AuthUserFactory, ProjectFactory, PreprintFactory
from tests.base import OsfTestCase


class FakeRequest:
    def __init__(self, user):
        self.user = user
        self.GET = {}


def make_event(**kwargs):
    defaults = {
        'download_type': DownloadEvent.FILE,
        'size_bytes': 1024 ** 3,
        'resource_guid': '',
    }
    defaults.update(kwargs)
    return DownloadEvent.objects.create(**defaults)


class TestDashboardAccess(OsfTestCase):
    """Membership in the allow-list group is the only key.

    Not a permission check — ModelBackend answers True to every permission for a
    superuser, which would defeat the point of the dashboard.
    """

    def setUp(self):
        super().setUp()
        self.admin = DownloadEventsView(DownloadEvent, AdminSite())
        self.group, _ = Group.objects.get_or_create(name=DASHBOARD_GROUP_NAME)

    def _user(self, in_group=False, superuser=False, with_perm=False):
        user = AuthUserFactory()
        user.is_staff = True
        user.is_superuser = superuser
        user.save()
        if in_group:
            self.group.user_set.add(user)
        if with_perm:
            user.user_permissions.add(Permission.objects.get(codename='view_downloadevent'))
        return type(user).objects.get(pk=user.pk)

    def test_group_member_gets_in(self):
        request = FakeRequest(self._user(in_group=True))

        assert self.admin.has_view_permission(request) is True
        assert self.admin.has_module_permission(request) is True

    def test_superuser_outside_the_group_is_locked_out(self):
        """The whole point: not even admins, unless they're on the list."""
        request = FakeRequest(self._user(superuser=True))

        assert self.admin.has_view_permission(request) is False
        assert self.admin.has_module_permission(request) is False

    def test_django_view_permission_alone_is_not_enough(self):
        request = FakeRequest(self._user(with_perm=True))

        assert self.admin.has_view_permission(request) is False

    def test_ordinary_staff_is_locked_out(self):
        request = FakeRequest(self._user())

        assert self.admin.has_view_permission(request) is False

    def test_it_is_read_only_even_for_group_members(self):
        """Append-only telemetry — nothing is editable through the admin."""
        request = FakeRequest(self._user(in_group=True))

        assert self.admin.has_add_permission(request) is False
        assert self.admin.has_change_permission(request) is False
        assert self.admin.has_delete_permission(request) is False

    def test_it_is_hidden_from_the_admin_index(self):
        """`has_module_permission` is what keeps it off the list of pages."""
        request = FakeRequest(self._user(superuser=True))

        assert self.admin.has_module_permission(request) is False


class TestDashboardData(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.admin = DownloadEventsView(DownloadEvent, AdminSite())

    def test_empty_range_does_not_blow_up(self):
        """The default window is the last hour, so empty is the normal case."""
        data = self.admin.get_dashboard_data(DownloadEvent.objects.none())

        assert data['summary']['total_downloads'] == 0
        assert data['summary']['total_gb'] == 0
        assert data['split']['file']['count_percent'] == 0
        assert data['split']['zip']['gb_percent'] == 0
        assert data['time_series']['labels'] == []
        assert data['top_projects'] == []

    def test_events_with_unknown_size_do_not_blow_up(self):
        """`size_bytes` is null when we could not determine it."""
        make_event(size_bytes=None, storage_region='Germany')
        make_event(size_bytes=None, download_type=DownloadEvent.PROJECT)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['summary']['total_downloads'] == 2
        assert data['summary']['total_gb'] == 0
        assert data['storage_regions'][0]['gb'] == 0

    def test_all_zero_sizes_do_not_blow_up(self):
        make_event(size_bytes=0, storage_region='Germany')
        make_event(size_bytes=0, storage_region='Germany')

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['storage_regions'][0]['gb_percent'] == 0

    def test_totals_and_split(self):
        make_event(size_bytes=2 * 1024 ** 3)
        make_event(size_bytes=2 * 1024 ** 3, download_type=DownloadEvent.PROJECT)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['summary']['total_downloads'] == 2
        assert data['summary']['total_gb'] == 4
        assert data['split']['file']['count_percent'] == 50
        assert data['split']['zip']['count_percent'] == 50

    def test_zip_outcomes_split_completed_cancelled_failed(self):
        # a completed zip, a user cancel (False at 200), and a failure (False at an error status)
        make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=True, status_code=200)
        make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=False, status_code=200)
        make_event(download_type=DownloadEvent.PROJECT, zip_completed=False, status_code=502)
        # a single file — has no outcome, must not land in any bucket
        make_event(download_type=DownloadEvent.FILE)

        outcomes = self.admin.get_dashboard_data(DownloadEvent.objects.all())['zip_outcomes']

        assert outcomes == {'completed': 1, 'cancelled': 1, 'failed': 1}

    def test_failed_zips_summary_counts_error_statuses(self):
        # any 4xx or 5xx that didn't complete is a failure; a 404 from an add-on provider
        # is just as much a failure as a 500 from our server
        make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=False, status_code=404)
        make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=False, status_code=500)
        make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=False, status_code=503)
        # a cancel (ended on a success status) must NOT count as failed
        make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=False, status_code=200)
        make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=True, status_code=200)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['summary']['failed_zips'] == 3

    def test_incomplete_zip_without_a_status_counts_as_cancelled(self):
        """Callbacks from a WaterButler build predating status_code have status None — treat
        those as cancels, not failures, so we never over-report failures."""
        make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=False, status_code=None)

        outcomes = self.admin.get_dashboard_data(DownloadEvent.objects.all())['zip_outcomes']

        assert outcomes == {'completed': 0, 'cancelled': 1, 'failed': 0}

    def test_outcome_column_labels(self):
        completed = make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=True)
        cancelled = make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=False, status_code=200)
        failed_5xx = make_event(download_type=DownloadEvent.PROJECT, zip_completed=False, status_code=500)
        # an add-on provider 404 is a failure, not a cancel
        failed_404 = make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=False, status_code=404)
        single = make_event(download_type=DownloadEvent.FILE)

        assert self.admin.outcome(completed) == 'Completed'
        assert self.admin.outcome(cancelled) == 'Cancelled'
        assert self.admin.outcome(failed_5xx) == 'Failed'
        assert self.admin.outcome(failed_404) == 'Failed'
        assert self.admin.outcome(single) == '—'

    def test_storage_provider_breakdown(self):
        make_event(storage_provider='osfstorage', size_bytes=3 * 1024 ** 3)
        make_event(storage_provider='osfstorage', size_bytes=1 * 1024 ** 3)
        make_event(storage_provider='github', size_bytes=2 * 1024 ** 3)

        providers = self.admin.get_dashboard_data(DownloadEvent.objects.all())['storage_providers']
        by_name = {row['name']: row for row in providers}

        assert by_name['osfstorage']['downloads'] == 2
        assert by_name['osfstorage']['gb'] == 4
        assert by_name['github']['downloads'] == 1
        assert by_name['github']['gb'] == 2

    def test_blank_storage_provider_folds_into_unknown(self):
        make_event(storage_provider='')

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        # Unknown is pulled out of the ranked list and reported on its own
        assert data['storage_providers'] == []
        assert data['storage_providers_unknown']['name'] == 'Unknown'
        assert data['storage_providers_unknown']['downloads'] == 1

    def test_region_breakdown_splits_requests_by_type(self):
        # Germany: 2 files + 1 folder zip + 1 project zip = 4 total, 3 zips
        make_event(storage_region='Germany', download_type=DownloadEvent.FILE)
        make_event(storage_region='Germany', download_type=DownloadEvent.FILE)
        make_event(storage_region='Germany', download_type=DownloadEvent.FOLDER_ZIP)
        make_event(storage_region='Germany', download_type=DownloadEvent.PROJECT)

        regions = self.admin.get_dashboard_data(DownloadEvent.objects.all())['storage_regions']
        germany = next(r for r in regions if r['name'] == 'Germany')

        assert germany['file_count'] == 2
        assert germany['zip_count'] == 2
        # file + zip always equals the total — the invariant QA will check
        assert germany['file_count'] + germany['zip_count'] == germany['downloads'] == 4

    def test_region_type_counts_match_the_period_totals(self):
        """Summed across regions, file/zip counts equal the header's split totals — so the
        subtitle and the bars can never disagree."""
        make_event(storage_region='Germany', download_type=DownloadEvent.FILE)
        make_event(storage_region='United States', download_type=DownloadEvent.FILE)
        make_event(storage_region='Germany', download_type=DownloadEvent.FOLDER_ZIP)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())
        regions = data['storage_regions']

        assert sum(r['file_count'] for r in regions) == data['split']['file']['count'] == 2
        assert sum(r['zip_count'] for r in regions) == data['split']['zip']['count'] == 1

    def test_region_type_counts_present_even_when_empty(self):
        data = self.admin.get_dashboard_data(DownloadEvent.objects.none())

        assert data['storage_regions'] == []
        assert data['user_regions'] == []

    def test_blank_and_null_regions_fold_into_unknown(self):
        make_event(storage_region='')
        make_event(storage_region='   ')

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        # blank and whitespace-only both mean "we couldn't tell" and fold into the
        # separate Unknown bucket, out of the ranked region list
        assert data['storage_regions'] == []
        assert data['storage_regions_unknown']['name'] == 'Unknown'
        assert data['storage_regions_unknown']['downloads'] == 2

    def test_unknown_is_separated_from_known_regions(self):
        """ENG: a large Unknown bucket must not crowd real regions off the chart. The
        ranked list holds only known regions; Unknown is reported on its own and the
        bars scale to the largest known region."""
        make_event(storage_region='Germany', size_bytes=5 * 1024 ** 3)
        make_event(storage_region='', size_bytes=1024 ** 3)
        make_event(storage_region='', size_bytes=1024 ** 3)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert [r['name'] for r in data['storage_regions']] == ['Germany']
        # scales to itself now that Unknown is out of the ranking
        assert data['storage_regions'][0]['gb_percent'] == 100
        assert data['storage_regions_unknown']['downloads'] == 2
        assert data['storage_regions_unknown']['gb'] == 2

    def test_no_unknown_bucket_when_every_region_resolves(self):
        make_event(storage_region='Germany', size_bytes=1024 ** 3)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['storage_regions_unknown'] is None

    def test_tb_suffix_only_appears_at_terabyte_scale(self):
        assert self.admin._tb_suffix(0) == ''
        assert self.admin._tb_suffix(500) == ''
        assert self.admin._tb_suffix(1023.9) == ''
        assert self.admin._tb_suffix(1024) == ' (1.0 TB)'
        assert self.admin._tb_suffix(2560) == ' (2.5 TB)'

    def test_total_gb_gets_a_tb_reading_when_terabyte_scale(self):
        make_event(size_bytes=2 * 1024 ** 4)  # 2 TB

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['summary']['total_gb'] == 2048
        assert data['summary']['total_gb_tb_suffix'] == ' (2.0 TB)'

    def test_sub_terabyte_total_has_no_tb_reading(self):
        make_event(size_bytes=3 * 1024 ** 3)  # 3 GB

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['summary']['total_gb_tb_suffix'] == ''

    def test_channel_breakdown_groups_by_channel(self):
        make_event(download_channel=DownloadEvent.FRONTEND, size_bytes=2 * 1024 ** 3)
        make_event(download_channel=DownloadEvent.FRONTEND, size_bytes=1024 ** 3)
        make_event(download_channel=DownloadEvent.API, size_bytes=1024 ** 3)
        make_event(download_channel='')  # recorded before the field / unresolved

        channels = self.admin.get_dashboard_data(DownloadEvent.objects.all())['channels']
        by_name = {c['name']: c for c in channels}

        assert by_name['Frontend (website)']['downloads'] == 2
        assert by_name['Frontend (website)']['gb'] == 3
        assert by_name['API client']['downloads'] == 1
        assert by_name['Unknown']['downloads'] == 1

    def test_channel_breakdown_orders_frontend_api_other_then_unknown(self):
        make_event(download_channel=DownloadEvent.OTHER)
        make_event(download_channel='')
        make_event(download_channel=DownloadEvent.FRONTEND)
        make_event(download_channel=DownloadEvent.API)

        channels = self.admin.get_dashboard_data(DownloadEvent.objects.all())['channels']

        assert [c['name'] for c in channels] == [
            'Frontend (website)', 'API client', 'Other / direct', 'Unknown',
        ]

    def test_top_projects_shows_title_and_guid(self):
        user = AuthUserFactory()
        node = ProjectFactory(creator=user, title='Panic Download Project')
        make_event(resource_guid=node._id, size_bytes=5 * 1024 ** 3)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['top_projects'][0]['name'] == f'Panic Download Project ({node._id})'
        assert data['top_projects'][0]['gb'] == 5

    def test_top_projects_falls_back_to_the_bare_guid(self):
        """An unresolvable guid still has to say something."""
        make_event(resource_guid='notaguid', size_bytes=1024 ** 3)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['top_projects'][0]['name'] == 'notaguid'

    def test_top_projects_resolves_preprint_title(self):
        """Preprints aren't nodes (and their guid can be versioned), but the name should
        still resolve — ENG-11849."""
        preprint = PreprintFactory(title='A Preprint About Downloads')
        make_event(resource_guid=preprint._id, size_bytes=4 * 1024 ** 3)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['top_projects'][0]['name'] == f'A Preprint About Downloads ({preprint._id})'

    def test_time_series_buckets_by_type(self):
        make_event(size_bytes=1024 ** 3)
        make_event(size_bytes=3 * 1024 ** 3, download_type=DownloadEvent.FOLDER_ZIP)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert len(data['time_series']['labels']) >= 1
        assert sum(data['time_series']['file']) == 1
        assert sum(data['time_series']['zip']) == 3

    def test_time_series_spans_gaps(self):
        """Quiet buckets render as zero instead of collapsing the axis."""
        recent = make_event(size_bytes=1024 ** 3)
        old = make_event(size_bytes=1024 ** 3)
        DownloadEvent.objects.filter(pk=old.pk).update(
            created=timezone.now() - timedelta(days=4)
        )
        DownloadEvent.objects.filter(pk=recent.pk).update(created=timezone.now())

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert len(data['time_series']['labels']) == 5
        assert data['time_series']['file'][0] == 1
        assert data['time_series']['file'][-1] == 1
        assert data['time_series']['file'][2] == 0

    def test_every_bucket_size_places_all_the_bytes(self):
        """The bucket key has to land on the same instant whether it came from an
        event or from walking the axis, at every granularity."""
        spans = {
            '15m': [timedelta(minutes=m) for m in (0, 20, 50, 80)],
            '1h': [timedelta(hours=h) for h in (0, 3, 9, 20)],
            '1d': [timedelta(days=d) for d in (0, 2, 5, 10)],
            '1w': [timedelta(days=d) for d in (0, 10, 20, 30)],
        }
        now = timezone.now()
        for bucket_size, offsets in spans.items():
            DownloadEvent.objects.all().delete()
            for offset in offsets:
                event = make_event(size_bytes=1024 ** 3)
                DownloadEvent.objects.filter(pk=event.pk).update(created=now - offset)

            series = self.admin._build_time_series(DownloadEvent.objects.all())

            assert sum(series['file']) == float(len(offsets)), (
                f'{bucket_size} buckets dropped data'
            )

    def test_time_series_with_a_single_event(self):
        """start == end, so the range delta is zero."""
        make_event(size_bytes=2 * 1024 ** 3)

        series = self.admin._build_time_series(DownloadEvent.objects.all())

        assert sum(series['file']) == 2.0

    def test_unique_users_ignores_anonymous(self):
        user = AuthUserFactory()
        make_event(user=user)
        make_event(user=user)
        make_event(user=None)

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert data['summary']['unique_users'] == 1


class TestSortableColumns(OsfTestCase):
    """Outcome and User are made sortable (ENG-11863, ENG-11864)."""

    def setUp(self):
        super().setUp()
        self.admin = DownloadEventsView(DownloadEvent, AdminSite())
        self.request = RequestFactory().get('/admin/osf/downloadevent/')

    def test_outcome_column_declares_a_sort_field(self):
        assert self.admin.outcome.admin_order_field == '_outcome_rank'

    def test_outcome_rank_orders_completed_cancelled_failed_then_single(self):
        completed = make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=True)
        cancelled = make_event(download_type=DownloadEvent.FOLDER_ZIP, zip_completed=False, status_code=200)
        failed = make_event(download_type=DownloadEvent.PROJECT, zip_completed=False, status_code=404)
        single = make_event(download_type=DownloadEvent.FILE)

        ordered = list(
            self.admin.get_queryset(self.request).order_by('_outcome_rank').values_list('id', flat=True)
        )

        assert ordered == [completed.id, cancelled.id, failed.id, single.id]

    def test_user_column_sorts_by_username_not_pk(self):
        assert self.admin.user_display.admin_order_field == 'user__username'

    def test_user_display_falls_back_for_anonymous(self):
        anon = make_event(user=None)
        assert self.admin.user_display(anon) == '—'

    def test_user_agent_column_declares_a_sort_field(self):
        assert self.admin.user_agent_display.admin_order_field == 'user_agent'

    def test_user_agent_display_shows_short_agents_in_full(self):
        event = make_event(user_agent='curl/8.0')
        assert self.admin.user_agent_display(event) == 'curl/8.0'

    def test_user_agent_display_truncates_long_agents(self):
        event = make_event(user_agent='Mozilla/5.0 ' + 'x' * 200)
        shown = self.admin.user_agent_display(event)
        assert len(shown) == 80 and shown.endswith('…')

    def test_user_agent_display_falls_back_when_blank(self):
        assert self.admin.user_agent_display(make_event(user_agent='')) == '—'

    def test_channel_column_declares_a_sort_field(self):
        assert self.admin.channel_display.admin_order_field == 'download_channel'

    def test_channel_display_shows_the_human_label(self):
        event = make_event(download_channel=DownloadEvent.API)
        assert self.admin.channel_display(event) == 'API client'

    def test_channel_display_falls_back_when_blank(self):
        assert self.admin.channel_display(make_event(download_channel='')) == '—'

    def test_outcome_annotation_does_not_change_dashboard_numbers(self):
        """Production feeds get_queryset() (annotated with _outcome_rank for sorting) into
        get_dashboard_data. The annotation must not alter any aggregate — guards against a
        stray GROUP BY. Full equality, since the region sort is now deterministic."""
        make_event(download_type=DownloadEvent.FILE, storage_region='Germany', size_bytes=2 * 1024 ** 3)
        make_event(download_type=DownloadEvent.FOLDER_ZIP, storage_region='Germany', zip_completed=True, size_bytes=3 * 1024 ** 3)
        make_event(download_type=DownloadEvent.PROJECT, storage_region='United States', zip_completed=False, status_code=404, size_bytes=5 * 1024 ** 3)

        annotated = self.admin.get_dashboard_data(self.admin.get_queryset(self.request))
        plain = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert annotated == plain


class TestDashboardFilters(OsfTestCase):
    """Project and user input filters (they also drive the charts, since the dashboard
    reads the same filtered changelist queryset)."""

    def setUp(self):
        super().setUp()
        self.admin = DownloadEventsView(DownloadEvent, AdminSite())

    def _make(self, filter_cls, params):
        request = RequestFactory().get('/admin/osf/downloadevent/', params)
        return filter_cls(request, dict(params), DownloadEvent, self.admin)

    def test_project_filter_scopes_to_one_guid(self):
        node = ProjectFactory()
        make_event(resource_guid=node._id)
        make_event(resource_guid='someotherguid')

        f = self._make(ProjectGuidFilter, {'project_guid': node._id})
        result = f.queryset(None, DownloadEvent.objects.all())

        assert list(result.values_list('resource_guid', flat=True)) == [node._id]

    def test_project_filter_ignores_surrounding_whitespace(self):
        node = ProjectFactory()
        make_event(resource_guid=node._id)

        f = self._make(ProjectGuidFilter, {'project_guid': f'  {node._id}  '})
        result = f.queryset(None, DownloadEvent.objects.all())

        assert result.count() == 1

    def test_user_filter_matches_by_email(self):
        user = AuthUserFactory()
        make_event(user=user)
        make_event(user=AuthUserFactory())

        f = self._make(DownloadUserFilter, {'download_user': user.username})
        result = f.queryset(None, DownloadEvent.objects.all())

        assert list(result.values_list('user_id', flat=True)) == [user.id]

    def test_user_filter_matches_by_guid(self):
        user = AuthUserFactory()
        make_event(user=user)
        make_event(user=AuthUserFactory())

        f = self._make(DownloadUserFilter, {'download_user': user._id})
        result = f.queryset(None, DownloadEvent.objects.all())

        assert list(result.values_list('user_id', flat=True)) == [user.id]

    def test_blank_filter_value_is_a_noop(self):
        make_event(resource_guid='a')
        make_event(resource_guid='b')

        f = self._make(ProjectGuidFilter, {})
        result = f.queryset(None, DownloadEvent.objects.all())

        assert result.count() == 2


class TestActiveFiltersBanner(OsfTestCase):
    """The read-only summary of what the dashboard is currently scoped to."""

    def setUp(self):
        super().setUp()
        self.admin = DownloadEventsView(DownloadEvent, AdminSite())

    def test_lists_applied_filters_with_labels(self):
        request = RequestFactory().get('/', {
            'project_guid': 'abcde',
            'download_user': 'a@b.com',
            'download_type': 'file',
            'q': 'chrome',
        })

        active = {f['label']: f['value'] for f in self.admin._active_filters(request)}

        assert active['Project'] == 'abcde'
        assert active['User'] == 'a@b.com'
        assert active['Download type'] == 'file'
        assert active['Search'] == 'chrome'

    def test_combines_the_date_range_halves(self):
        request = RequestFactory().get('/', {
            'created__range__gte_0': '2026-01-01',
            'created__range__gte_1': '00:00:00',
            'created__range__lte_0': '2026-01-02',
            'created__range__lte_1': '12:00:00',
        })

        active = self.admin._active_filters(request)
        date = next(f for f in active if f['label'] == 'Date (UTC)')

        assert date['value'] == '2026-01-01 00:00:00 → 2026-01-02 12:00:00'

    def test_empty_when_no_filters_applied(self):
        request = RequestFactory().get('/')

        assert self.admin._active_filters(request) == []


class TestStaffAccessMigration(OsfTestCase):
    """Django's admin rejects anyone without `is_staff` before our gate runs, so
    the allow-listed users need it to reach the page at all."""

    def setUp(self):
        super().setUp()
        from importlib import import_module
        self.migration = import_module('osf.migrations.0046_dashboard_group_staff_access')
        self.group, _ = Group.objects.get_or_create(name=DASHBOARD_GROUP_NAME)

    def test_it_grants_staff_to_group_members_only(self):
        member = AuthUserFactory()
        outsider = AuthUserFactory()
        self.group.user_set.add(member)

        self.migration.grant_staff_access(global_apps, None)

        member.refresh_from_db()
        outsider.refresh_from_db()
        assert member.is_staff is True
        assert outsider.is_staff is False

    def test_it_does_not_grant_superuser(self):
        """is_staff opens the admin door; is_superuser would bypass every gate."""
        member = AuthUserFactory()
        self.group.user_set.add(member)

        self.migration.grant_staff_access(global_apps, None)

        member.refresh_from_db()
        assert member.is_superuser is False

    def test_reversing_does_not_strip_staff_from_existing_admins(self):
        admin_user = AuthUserFactory()
        admin_user.is_staff = True
        admin_user.save()
        self.group.user_set.add(admin_user)

        self.migration.revoke_staff_access(global_apps, None)

        admin_user.refresh_from_db()
        assert admin_user.is_staff is True
