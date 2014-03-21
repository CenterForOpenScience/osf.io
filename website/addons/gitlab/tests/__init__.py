import mock
from webtest_plus import TestApp

from website.app import init_app
from website.addons.base.testing import AddonTestCase

app = init_app(
    routes=True, set_backends=False, settings_module='website.settings',
)

class GitlabTestCase(AddonTestCase):

    ADDON_SHORT_NAME = 'gitlab'

    def create_app(self):
        return TestApp(app)

    def set_user_settings(self, settings):
        settings.user_id = 1

    def set_node_settings(self, settings):
        settings.project_id = 1

    def setUp(self):

        self.patch_create_user = mock.patch('website.addons.gitlab.model.create_user')
        self.mock_create_user = self.patch_create_user.start()
        super(GitlabTestCase, self).setUp()
