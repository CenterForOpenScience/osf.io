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
        u'approvals_before_merge': 0,
        u'archived': False,
        u'avatar_url': None,
        u'builds_enabled': True,
        u'container_registry_enabled': True,
        u'created_at': u'2017-07-05T16:40:26.428Z',
        u'creator_id': 1444024,
        u'default_branch': u'master',
        u'description': u'For testing',
        u'forks_count': 0,
        u'http_url_to_repo': u'https://gitlab.com/{}/mock-repo.git'.format(user),
        u'id': 3643758,
        u'issues_enabled': True,
        u'last_activity_at': u'2017-07-05T16:40:26.428Z',
        u'lfs_enabled': True,
        u'merge_requests_enabled': True,
        u'name': u'mock-repo',
        u'name_with_namespace': u'{} / mock-repo'.format(user),
        u'namespace': {u'full_path': u'{}'.format(user),
            u'id': 1748448,
            u'kind': u'user',
            u'name': u'{}'.format(user),
            u'path': u'{}'.format(user)},
        u'only_allow_merge_if_all_discussions_are_resolved': False,
        u'only_allow_merge_if_build_succeeds': False,
        u'open_issues_count': 0,
        u'owner': {u'avatar_url': u'https://secure.gravatar.com/avatar/a7fa245b01a35ad586d8e2fa5bd7be5f?s=80&d=identicon',
            u'id': 1444024,
            u'name': u'{}'.format(user),
            u'state': u'active',
            u'username': u'{}'.format(user),
            u'web_url': u'https://gitlab.com/{}'.format(user)},
        u'path': u'mock-repo',
        u'path_with_namespace': u'{}/mock-repo'.format(user),
        u'permissions': {u'group_access': None,
            u'project_access': {u'access_level': 40, u'notification_level': 3}},
        u'public': False,
        u'public_builds': True,
        u'request_access_enabled': False,
        u'shared_runners_enabled': True,
        u'shared_with_groups': [],
        u'snippets_enabled': True,
        u'ssh_url_to_repo': u'git@gitlab.com:{}/mock-repo.git'.format(user),
        u'star_count': 0,
        u'tag_list': [],
        u'visibility_level': 0,
        u'web_url': u'https://gitlab.com/{}/mock-repo'.format(user),
        u'wiki_enabled': True
    })

    branch = mock.Mock(**{
        u'commit': {u'author_email': u'{}@gmail.com'.format(user),
            u'author_name': u''.format(user),
            u'authored_date': u'2017-07-05T16:43:04.000+00:00',
            u'committed_date': u'2017-07-05T16:43:04.000+00:00',
            u'committer_email': u'{}@gmail.com'.format(user),
            u'committer_name': u'{}'.format(user),
            u'created_at': u'2017-07-05T16:43:04.000+00:00',
            u'id': u'f064566f133ddfad636ceec72c5937cc0044c371',
            u'message': u'Add readme.md',
            u'parent_ids': [],
            u'short_id': u'f064566f',
            u'title': u'Add readme.md'},
        u'developers_can_merge': False,
        u'developers_can_push': False,
        u'merged': False,
        u'protected': True
    })

    # Hack because 'name' is a reserved keyword in a Mock object
    type(branch).name = 'master'

    gitlab_mock.branches.return_value = [branch]

    return gitlab_mock
