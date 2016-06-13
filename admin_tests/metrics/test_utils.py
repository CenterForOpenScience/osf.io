from nose import tools as nt
from datetime import timedelta, datetime

from tests.base import AdminTestCase
from tests.factories import (
    AuthUserFactory, NodeFactory, ProjectFactory, RegistrationFactory
)

from website.project.model import Node, User
from framework.auth import Auth

from admin.metrics.utils import (
    get_projects,
    get_osf_statistics,
    get_list_of_dates,
    get_previous_midnight,
    get_days_statistics,
    DAY_LEEWAY,
    get_active_user_count,
    get_unregistered_users,
)
from admin.metrics.models import OSFWebsiteStatistics


class TestMetricsGetProjects(AdminTestCase):
    def setUp(self):
        super(TestMetricsGetProjects, self).setUp()
        Node.remove()
        self.public_node = ProjectFactory(is_public=True)
        self.private_node = ProjectFactory(is_public=False)
        self.node_2 = NodeFactory()  # creates parent project + node
        self.reg = RegistrationFactory(project=self.public_node)

    def test_get_all_top_level_nodes(self):
        count = get_projects()
        nt.assert_equal(count, 4)

    def test_get_public_top_level_nodes(self):
        count = get_projects(public=True)
        nt.assert_equal(count, 1)

    def test_get_registrations(self):
        count = get_projects(registered=True)
        nt.assert_equal(count, 1)

    def test_date_created_filter_returns_no_results(self):
        time = self.public_node.date_created - timedelta(weeks=1)
        count = get_projects(time=time)
        nt.assert_equal(count, 0)


class TestMetricsGetDaysStatistics(AdminTestCase):
    def setUp(self):
        super(TestMetricsGetDaysStatistics, self).setUp()
        Node.remove()
        NodeFactory(category='project')  # makes Node, plus parent
        NodeFactory(category='data')

    def test_time_now(self):
        get_days_statistics(datetime.utcnow())
        nt.assert_equal(OSFWebsiteStatistics.objects.count(), 1)
        nt.assert_equal(OSFWebsiteStatistics.objects.latest('date').projects, 2)

    def test_delta(self):
        get_days_statistics(datetime.utcnow())
        ProjectFactory()
        ProjectFactory()
        latest = OSFWebsiteStatistics.objects.latest('date')
        get_days_statistics(datetime.utcnow(), latest)
        even_later = OSFWebsiteStatistics.objects.latest('date')
        nt.assert_equal(even_later.delta_projects, 2)


class TestMetricsGetOSFStatistics(AdminTestCase):
    def setUp(self):
        super(TestMetricsGetOSFStatistics, self).setUp()
        Node.remove()
        time_now = get_previous_midnight()
        NodeFactory(category='project', date_created=time_now)
        NodeFactory(category='project',
                    date_created=time_now - timedelta(days=1))
        last_time = time_now - timedelta(days=2)
        NodeFactory(category='project', date_created=last_time)
        NodeFactory(category='project', date_created=last_time)
        get_days_statistics(last_time + timedelta(seconds=1))
        self.time = time_now + timedelta(seconds=1)

    def test_get_two_more_days(self):
        nt.assert_equal(OSFWebsiteStatistics.objects.count(), 1)
        get_osf_statistics()
        nt.assert_equal(OSFWebsiteStatistics.objects.count(), 3)

    def test_dont_add_another(self):
        nt.assert_equal(OSFWebsiteStatistics.objects.count(), 1)
        get_osf_statistics()
        nt.assert_equal(OSFWebsiteStatistics.objects.count(), 3)
        get_osf_statistics()
        nt.assert_equal(OSFWebsiteStatistics.objects.count(), 3)


class TestMetricListDays(AdminTestCase):
    def test_five_days(self):
        time_now = datetime.utcnow()
        time_past = time_now - timedelta(days=5)
        dates = get_list_of_dates(time_past, time_now)
        nt.assert_equal(len(dates), 5)
        nt.assert_in(time_now, dates)

    def test_month_transition(self):
        time_now = datetime.utcnow()
        time_end = time_now - timedelta(
            days=(time_now.day - 2)
        )
        time_start = time_end - timedelta(days=5)
        dates = get_list_of_dates(time_start, time_end)
        nt.assert_equal(len(dates), 5)

    def test_off_by_seconds(self):
        time_now = datetime.utcnow()
        time_start = time_now - timedelta(
            seconds=DAY_LEEWAY + 1
        )
        dates = get_list_of_dates(time_start, time_now)
        nt.assert_equal(len(dates), 1)

    def test_on_exact_time(self):
        time_now = datetime.utcnow()
        time_start = time_now - timedelta(
            seconds=DAY_LEEWAY
        )
        dates = get_list_of_dates(time_start, time_now)
        nt.assert_equal(len(dates), 0)

    def test_just_missed_time(self):
        time_now = datetime.utcnow()
        time_start = time_now - timedelta(
            seconds=DAY_LEEWAY - 1
        )
        dates = get_list_of_dates(time_start, time_now)
        nt.assert_equal(len(dates), 0)


class TestMetricPreviousMidnight(AdminTestCase):
    def test_midnight(self):
        time_now = datetime.utcnow()
        midnight = get_previous_midnight(time_now)
        nt.assert_equal(midnight.date(), time_now.date())
        nt.assert_equal(midnight.hour, 0)
        nt.assert_equal(midnight.minute, 0)
        nt.assert_equal(midnight.second, 0)
        nt.assert_equal(midnight.microsecond, 1)

    def test_no_time_given(self):
        time_now = datetime.utcnow()
        midnight = get_previous_midnight()
        nt.assert_equal(midnight.date(), time_now.date())


class TestUserGet(AdminTestCase):
    def setUp(self):
        super(TestUserGet, self).setUp()
        User.remove()
        self.user_1 = AuthUserFactory()
        self.auth = Auth(user=self.user_1)
        self.project = ProjectFactory(creator=self.user_1)
        self.project.add_unregistered_contributor(
            email='foo@bar.com',
            fullname='Weezy F. Baby',
            auth=self.auth
        )
        self.user_3 = AuthUserFactory()
        self.user_3.date_confirmed = None
        self.user_3.save()
        self.user_4 = AuthUserFactory()

    def test_get_all_user_count(self):
        time_now = datetime.utcnow()
        count = get_active_user_count(time_now)
        nt.assert_equal(count, 2)

    def test_get_unregistered_users(self):
        count = get_unregistered_users()
        nt.assert_equal(count, 1)
