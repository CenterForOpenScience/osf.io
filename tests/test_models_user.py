from nose.tools import *

from website import models
from tests import base
from tests import factories


class UserTestCase(base.OsfTestCase):
    def setUp(self):
        super(UserTestCase, self).setUp()
        self.user = factories.AuthUserFactory()
        self.unregistered = factories.UnregUserFactory()
        self.unconfirmed = factories.UnconfirmedUserFactory()
        self.USERS = (self.user, self.unregistered, self.unconfirmed)

        for user in self.USERS:
            factories.ProjectFactory(creator=user)

    def tearDown(self):
        models.Node.remove()
        models.User.remove()
        super(UserTestCase, self).tearDown()

    def test_can_be_merged(self):
        assert_false(self.user.can_be_merged)
        assert_true(self.unregistered.can_be_merged)
        assert_true(self.unconfirmed.can_be_merged)
