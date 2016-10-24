from datetime import datetime, timedelta
from nose.tools import *  # noqa

from website.models import User
from tests.base import OsfTestCase
from tests.factories import AuthUserFactory
from scripts.analytics.user_count import count


class TestUserCount(OsfTestCase):
    def setUp(self):
        self.today = datetime.today()
        self.a_while_ago = self.today - timedelta(2)
        super(TestUserCount, self).setUp()
        for i in range(0, 3):
            u = AuthUserFactory()
            u.is_registered = True
            u.password = 'wow' + str(i)
            u.date_confirmed = self.today
            u.save()
        u = AuthUserFactory()
        u.is_registered = True
        u.password = 'wow'
        u.date_confirmed = self.a_while_ago
        u.save()
        for i in range(0, 2):
            u = AuthUserFactory()
            u.date_confirmed = None
            u.save()
        u = AuthUserFactory()
        u.date_disabled = self.today
        u.save()
        u = AuthUserFactory()
        u.date_disabled = self.a_while_ago
        u.save()

    def tearDown(self):
        User.remove()

    def test_gets_users(self):
        data = count(self.today + timedelta(1))
        assert_equal(data['active_users'], 4)
        assert_equal(data['unconfirmed_users'], 2)
        assert_equal(data['deactivated_users'], 2)

    def test_gets_only_users_from_given_date(self):
        data = count(self.today - timedelta(1))
        assert_equal(data['active_users'], 1)
        assert_equal(data['unconfirmed_users'], 0)
        assert_equal(data['deactivated_users'], 1)
