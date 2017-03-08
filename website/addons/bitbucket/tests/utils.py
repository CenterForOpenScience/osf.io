import mock

from website.addons.bitbucket.api import BitbucketClient

from website.addons.base.testing import OAuthAddonTestCaseMixin, AddonTestCase
from website.addons.bitbucket.model import BitbucketProvider
from website.addons.bitbucket.tests.factories import BitbucketAccountFactory


class BitbucketAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):
    ADDON_SHORT_NAME = 'bitbucket'
    ExternalAccountFactory = BitbucketAccountFactory
    Provider = BitbucketProvider

    def set_node_settings(self, settings):
        super(BitbucketAddonTestCase, self).set_node_settings(settings)
        settings.repo = 'abc'
        settings.user = 'octo-cat'

def mock_get_user():
    pass

def mock_user():
    pass

def mock_repo():
    pass

def mock_repos():
    pass

def mock_get_repo_default_branch():
    pass

def mock_branches():
    pass
