from webtest_plus import TestApp

from website import settings
from website.app import init_app
from website.addons.base.testing import AddonTestCase

app = init_app(
    routes=True, set_backends=False, settings_module='website.settings',
)


class GitlabTestCase(AddonTestCase):

    TEST_FOR = settings.ADDONS_AVAILABLE_DICT['gitlab']

    def create_app(self):
        return TestApp(app)

    def set_user_settings(self, settings):
        settings.user_id = 1

    def set_node_settings(self, settings):
        settings.project_id = 1
