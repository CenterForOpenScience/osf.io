import mock
from addons.gitlab.api import GitLabClient

from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.gitlab.models import GitLabProvider
from addons.gitlab.tests.factories import GitLabAccountFactory


class GitLabAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):
    ADDON_SHORT_NAME = 'gitlab'
    ExternalAccountFactory = GitLabAccountFactory
    Provider = GitLabProvider

    def set_node_settings(self, settings):
        super(GitLabAddonTestCase, self).set_node_settings(settings)
        settings.repo = 'osfgitlabtest'
        settings.user = 'osfio'

def create_mock_gitlab(user='osfio', private=False):
    """Factory for mock GitLab objects.
    Example: ::

        >>> gitlab = create_mock_gitlab(user='osfio')
        >>> gitlab.branches(user='osfio', repo='hello-world')
        >>> [{u'commit': {u'sha': u'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
        ...   u'url': u'https://api.gitlab.com/repos/osfio/mock-repo/commits/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'},
        ...  u'name': u'dev'},
        ... {u'commit': {u'sha': u'444a74d0d90a4aea744dacb31a14f87b5c30759c',
        ...   u'url': u'https://api.gitlab.com/repos/osfio/mock-repo/commits/444a74d0d90a4aea744dacb31a14f87b5c30759c'},
        ...  u'name': u'master'},
        ... {u'commit': {u'sha': u'c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
        ...   u'url': u'https://api.gitlab.com/repos/osfio/mock-repo/commits/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6'},
        ...  u'name': u'no-bundle'}]

    :param str user: GitLab username.
    :param bool private: Whether repo is private.
    :return: An autospecced GitLab Mock object
    """
    gitlab_mock = mock.create_autospec(GitLabClient)

    gitlab_mock.repo = mock.Mock(**{
        'approvals_before_merge': 0,
        'archived': False,
        'avatar_url': None,
        'builds_enabled': True,
        'container_registry_enabled': True,
        'created_at': '2017-07-05T16:40:26.428Z',
        'creator_id': 1444024,
        'default_branch': 'master',
        'description': 'For testing',
        'forks_count': 0,
        'http_url_to_repo': 'https://gitlab.com/{}/mock-repo.git'.format(user),
        'id': 3643758,
        'issues_enabled': True,
        'last_activity_at': '2017-07-05T16:40:26.428Z',
        'lfs_enabled': True,
        'merge_requests_enabled': True,
        'name': 'mock-repo',
        'name_with_namespace': '{} / mock-repo'.format(user),
        'namespace': {'full_path': '{}'.format(user),
            'id': 1748448,
            'kind': 'user',
            'name': '{}'.format(user),
            'path': '{}'.format(user)},
        'only_allow_merge_if_all_discussions_are_resolved': False,
        'only_allow_merge_if_build_succeeds': False,
        'open_issues_count': 0,
        'owner': {'avatar_url': 'https://secure.gravatar.com/avatar/a7fa245b01a35ad586d8e2fa5bd7be5f?s=80&d=identicon',
            'id': 1444024,
            'name': '{}'.format(user),
            'state': 'active',
            'username': '{}'.format(user),
            'web_url': 'https://gitlab.com/{}'.format(user)},
        'path': 'mock-repo',
        'path_with_namespace': '{}/mock-repo'.format(user),
        'permissions': {'group_access': None,
            'project_access': {'access_level': 40, 'notification_level': 3}},
        'public': False,
        'public_builds': True,
        'request_access_enabled': False,
        'shared_runners_enabled': True,
        'shared_with_groups': [],
        'snippets_enabled': True,
        'ssh_url_to_repo': 'git@gitlab.com:{}/mock-repo.git'.format(user),
        'star_count': 0,
        'tag_list': [],
        'visibility_level': 0,
        'web_url': 'https://gitlab.com/{}/mock-repo'.format(user),
        'wiki_enabled': True
    })

    branch = mock.Mock(**{
        'commit': {'author_email': '{}@gmail.com'.format(user),
            'author_name': ''.format(user),
            'authored_date': '2017-07-05T16:43:04.000+00:00',
            'committed_date': '2017-07-05T16:43:04.000+00:00',
            'committer_email': '{}@gmail.com'.format(user),
            'committer_name': '{}'.format(user),
            'created_at': '2017-07-05T16:43:04.000+00:00',
            'id': 'f064566f133ddfad636ceec72c5937cc0044c371',
            'message': 'Add readme.md',
            'parent_ids': [],
            'short_id': 'f064566f',
            'title': 'Add readme.md'},
        'developers_can_merge': False,
        'developers_can_push': False,
        'merged': False,
        'protected': True
    })

    # Hack because 'name' is a reserved keyword in a Mock object
    type(branch).name = 'master'

    gitlab_mock.branches.return_value = [branch]

    return gitlab_mock
