from website import settings
from website.addons.base.testing import AddonTestCase


class GitlabTestCase(AddonTestCase):

    TEST_FOR = settings.ADDONS_AVAILABLE_DICT['gitlab']
    PATCH_GITLAB = False

    def set_user_settings(self, settings):
        settings.user_id = 1

    def set_node_settings(self, settings):
        settings.project_id = 1
