from nose.tools import *

from tests.base import fake

from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab.views import hooks
from website.addons.gitlab.tests import GitlabTestCase

class TestHookLog(GitlabTestCase):

    def setUp(self):
        super(TestHookLog, self).setUp()

    def test_add_log_from_osf(self):
        log_count = len(self.project.logs)
        payload = {
            'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
            'message': gitlab_settings.MESSAGES['add'],
            'timestamp': '2014-03-31T13:40:39+00:00',
            'author': {
                'name': self.user.fullname,
                'email': self.user.username,
            }
        }
        hooks.add_hook_log(self.node_settings, payload, save=True)
        self.project.reload()
        assert_equal(
            len(self.project.logs),
            log_count
        )

    def test_add_log_from_osf_user(self):
        log_count = len(self.project.logs)
        payload = {
            'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
            'message': 'pushed from git',
            'timestamp': '2014-03-31T13:40:39+00:00',
            'author': {
                'name': self.user.fullname,
                'email': self.user.username,
            }
        }
        hooks.add_hook_log(self.node_settings, payload, save=True)
        self.project.reload()
        assert_equal(
            len(self.project.logs),
            log_count + 1
        )
        assert_equal(self.project.logs[-1].user, self.user)
        assert_equal(self.project.logs[-1].foreign_user,  None)

    def test_add_log_from_non_osf_user(self):
        name, email = fake.name(), fake.email()
        log_count = len(self.project.logs)
        payload = {
            'id': '47b79b37ef1cf6f944f71ea13c6667ddd98b9804',
            'message': 'pushed from git',
            'timestamp': '2014-03-31T13:40:39+00:00',
            'author': {
                'name': name,
                'email': email,
            }
        }
        hooks.add_hook_log(self.node_settings, payload, save=True)
        self.project.reload()
        assert_equal(
            len(self.project.logs),
            log_count + 1
        )
        assert_equal(self.project.logs[-1].user, None)
        assert_equal(self.project.logs[-1].foreign_user, name)
