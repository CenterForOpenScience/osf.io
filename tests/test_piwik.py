from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory
from tests.test_features import requires_piwik


@requires_piwik
class TestCreateUser(OsfTestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_has_piwik_token(self):
        assert_true(self.user.piwik_token)

@requires_piwik
class TestCreateProject(OsfTestCase):
    def setUp(self):
        self.project = ProjectFactory()

    def test_has_piwik_site_id(self):
        assert_true(self.project.piwik_site_id)
