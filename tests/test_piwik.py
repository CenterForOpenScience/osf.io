from nose.tools import *

from tests.base import DbTestCase, AppTestCase
from tests.factories import ProjectFactory, UserFactory


class TestCreateUser(DbTestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_has_piwik_token(self):
        assert_true(self.user.piwik_token)

class TestCreateProject(DbTestCase):
    def setUp(self):
        self.project = ProjectFactory()

    def test_has_piwik_site_id(self):
        assert_true(self.project.piwik_site_id)
