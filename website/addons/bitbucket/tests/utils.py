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

def create_mock_bitbucket(user='octo-cat', private=False):
    """Factory for mock BitbucketClients objects.
    Example: ::
    """

    bitbucket_mock = mock.create_autospec(BitbucketClient)
    bitbucket_mock.username.return_value = user
    bitbucket_mock.user.return_value = {  # TODO: needs filling out
        'username': user,
        'uuid': '1234-3324',
        'links': {'html': {'ref': 'https://nope.example.org/profile.html'}},
    }

    bitbucket_mock.repo.return_value = {
        'name': 'cow-problems-app',
        'is_private': private,
        'owner': {'username': user},
    }
    bitbucket_mock.repos.return_value = [
        {'name': 'cow-problems-app',   'owner': {'username': user}, 'is_private': private},
        {'name': 'duck-problems-app',  'owner': {'username': user}, 'is_private': True},
        {'name': 'horse-problems-app', 'owner': {'username': user}, 'is_private': False},
    ]
    bitbucket_mock.team_repos.return_value = [
        {'name': 'pig-problems-app',   'owner': {'username': 'team-barn-devs'}, 'is_private': private},
        {'name': 'goat-problems-app',  'owner': {'username': 'team-barn-devs'}, 'is_private': True},
        {'name': 'goose-problems-app', 'owner': {'username': 'team-barn-devs'}, 'is_private': False},

    ]

    bitbucket_mock.repo_default_branch.return_value = 'master'
    bitbucket_mock.branches.return_value = [
        {'name': 'master',  'target': {'hash': 'a1b2c3d4'}},
        {'name': 'develop', 'target': {'hash': '0f9e8d7c'}},
    ]

    return bitbucket_mock
