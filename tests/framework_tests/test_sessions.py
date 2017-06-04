from nose.tools import *

from framework.sessions import utils
from tests import factories
from tests.base import DbTestCase
from tests.factories import SessionFactory
from website.models import User
from website.models import Session


class SessionUtilsTestCase(DbTestCase):
    def setUp(self, *args, **kwargs):
        super(SessionUtilsTestCase, self).setUp(*args, **kwargs)
        self.user = factories.UserFactory()

    def tearDown(self, *args, **kwargs):
        super(SessionUtilsTestCase, self).tearDown(*args, **kwargs)
        User.remove()
        Session.remove()

    def test_remove_session_for_user(self):
        SessionFactory(user=self.user)

        # sanity check
        assert_equal(1, Session.find().count())

        utils.remove_sessions_for_user(self.user)
        assert_equal(0, Session.find().count())

        SessionFactory()
        SessionFactory(user=self.user)

        # sanity check
        assert_equal(2, Session.find().count())

        utils.remove_sessions_for_user(self.user)
        assert_equal(1, Session.find().count())

    def test_password_change_clears_sessions(self):
        SessionFactory(user=self.user)
        SessionFactory(user=self.user)
        SessionFactory(user=self.user)
        assert_equal(3, Session.find().count())
        self.user.set_password('killerqueen')
        assert_equal(0, Session.find().count())

    def test_remove_session(self):
        session = SessionFactory(user=self.user)
        assert_equal(1, Session.find().count())
        utils.remove_session(session)
        assert_equal(0, Session.find().count())
