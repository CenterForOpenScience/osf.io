from datetime import timedelta

from django.apps import apps as global_apps
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import Group, Permission
from django.utils import timezone

from osf.admin import DASHBOARD_GROUP_NAME, DownloadEventsView
from osf.models import DownloadEvent
from osf_tests.factories import AuthUserFactory, ProjectFactory
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

    def test_blank_and_null_regions_fold_into_unknown(self):
        make_event(storage_region='')
        make_event(storage_region='   ')

        data = self.admin.get_dashboard_data(DownloadEvent.objects.all())

        assert [row['name'] for row in data['storage_regions']] == ['Unknown']
        assert data['storage_regions'][0]['downloads'] == 2

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
