from unittest import mock
from json import dumps
import github3
from addons.github.api import GitHubClient
from github3.repos.branch import Branch

from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.github.models import GitHubProvider
from addons.github.tests.factories import GitHubAccountFactory


class GitHubAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):
    ADDON_SHORT_NAME = 'github'
    ExternalAccountFactory = GitHubAccountFactory
    Provider = GitHubProvider

    def set_node_settings(self, settings):
        super().set_node_settings(settings)
        settings.repo = 'abc'
        settings.user = 'octo-cat'
        settings.save()

# TODO: allow changing the repo name
def create_mock_github(user='octo-cat', private=False):
    """Factory for mock GitHub objects.
    Example: ::

        >>> github = create_mock_github(user='octocat')
        >>> github.branches(user='octocat', repo='hello-world')
        >>> [{u'commit': {u'sha': u'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
        ...   u'url': u'https://api.github.com/repos/octocat/mock-repo/commits/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'},
        ...  u'name': u'dev'},
        ... {u'commit': {u'sha': u'444a74d0d90a4aea744dacb31a14f87b5c30759c',
        ...   u'url': u'https://api.github.com/repos/octocat/mock-repo/commits/444a74d0d90a4aea744dacb31a14f87b5c30759c'},
        ...  u'name': u'master'},
        ... {u'commit': {u'sha': u'c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
        ...   u'url': u'https://api.github.com/repos/octocat/mock-repo/commits/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6'},
        ...  u'name': u'no-bundle'}]

    :param str user: Github username.
    :param bool private: Whether repo is private.
    :return: An autospecced GitHub Mock object
    """
    github_mock = mock.create_autospec(GitHubClient)
    github_mock.repo.return_value = github3.repos.Repository.from_json(dumps({
     'archive_url': f'https://api.github.com/repos/{user}/mock-repo/{{archive_format}}{{/ref}}',
     'assignees_url': f'https://api.github.com/repos/{user}/mock-repo/assignees{{/user}}',
     'blobs_url': f'https://api.github.com/repos/{user}/mock-repo/git/blobs{{/sha}}',
     'branches_url': f'https://api.github.com/repos/{user}/mock-repo/branches{{/bra.format(user=user)nch}}',
     'clone_url': f'https://github.com/{user}/mock-repo.git',
     'collaborators_url': f'https://api.github.com/repos/{user}/mock-repo/collaborators{{/collaborator}}',
     'comments_url': f'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}',
     'commits_url': f'https://api.github.com/repos/{user}/mock-repo/commits{{/sha}}',
     'compare_url': 'https://api.github.com/repos/{user}/mock-repo/compare/{{base}}...{{head}}',
     'contents_url': f'https://api.github.com/repos/{user}/mock-repo/contents/{{+path}}',
     'contributors_url': f'https://api.github.com/repos/{user}/mock-repo/contributors',
     'created_at': '2013-06-30T18:29:18Z',
     'default_branch': 'dev',
     'description': 'Simple, Pythonic, text processing--Sentiment analysis, part-of-speech tagging, noun phrase extraction, translation, and more.',
     'downloads_url': f'https://api.github.com/repos/{user}/mock-repo/downloads',
     'events_url': f'https://api.github.com/repos/{user}/mock-repo/events',
     'fork': False,
     'forks': 89,
     'forks_count': 89,
     'forks_url': 'https://api.github.com/repos/{user}/mock-repo/forks',
     'full_name': '{user}/mock-repo',
     'git_commits_url': f'https://api.github.com/repos/{user}/mock-repo/git/commits{{/sha}}',
     'git_refs_url': f'https://api.github.com/repos/{user}/mock-repo/git/refs{{/sha}}',
     'git_tags_url': f'https://api.github.com/repos/{user}/mock-repo/git/tags{{/sha}}',
     'git_url': f'git://github.com/{user}/mock-repo.git',
     'has_downloads': True,
     'has_issues': True,
     'has_wiki': True,
     'homepage': 'https://mock-repo.readthedocs.org/',
     'hooks_url': f'https://api.github.com/repos/{user}/mock-repo/hooks',
     'html_url': f'https://github.com/{user}/mock-repo',
     'id': 11075275,
     'issue_comment_url': f'https://api.github.com/repos/{user}/mock-repo/issues/comments/{{number}}',
     'issue_events_url': f'https://api.github.com/repos/{user}/mock-repo/issues/events{{/number}}',
     'issues_url': f'https://api.github.com/repos/{user}/mock-repo/issues{{/number}}',
     'keys_url': f'https://api.github.com/repos/{user}/mock-repo/keys{{/key_id}}',
     'labels_url': f'https://api.github.com/repos/{user}/mock-repo/labels{{/name}}',
     'language': 'Python',
     'languages_url': f'https://api.github.com/repos/{user}/mock-repo/languages',
     'master_branch': 'dev',
     'merges_url': f'https://api.github.com/repos/{user}/mock-repo/merges',
     'milestones_url': f'https://api.github.com/repos/{user}/mock-repo/milestones{{/number}}',
     'mirror_url': None,
     'name': 'mock-repo',
     'network_count': 89,
     'notifications_url': f'https://api.github.com/repos/{user}/mock-repo/notifications{{?since,all,participating}}',
     'open_issues': 2,
     'open_issues_count': 2,
     'owner': {'avatar_url': 'https://gravatar.com/avatar/c74f9cfd7776305a82ede0b765d65402?d=https%3A%2F%2Fidenticons.github.com%2F3959fe3bcd263a12c28ae86a66ec75ef.png&r=x',
      'events_url': f'https://api.github.com/users/{user}/events{{/privacy}}',
      'followers_url': f'https://api.github.com/users/{user}/followers',
      'following_url': f'https://api.github.com/users/{user}/following{{/other_user}}',
      'gists_url': f'https://api.github.com/users/{user}/gists{{/gist_id}}',
      'gravatar_id': 'c74f9cfd7776305a82ede0b765d65402',
      'html_url': f'https://github.com/{user}',
      'id': 2379650,
      'login': user,
      'organizations_url': f'https://api.github.com/users/{user}/orgs',
      'received_events_url': 'https://api.github.com/users/{user}/received_events',
      'repos_url': f'https://api.github.com/users/{user}/repos',
      'site_admin': False,
      'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}',
      'subscriptions_url': f'https://api.github.com/users/{user}/subscriptions',
      'type': 'User',
      'url': f'https://api.github.com/users/{user}'},
     'private': private,
     'pulls_url': f'https://api.github.com/repos/{user}/mock-repo/pulls{{/number}}',
     'pushed_at': '2013-12-30T16:05:54Z',
     'releases_url': f'https://api.github.com/repos/{user}/mock-repo/releases{{/id}}',
     'size': 8717,
     'ssh_url': f'git@github.com:{user}/mock-repo.git',
     'stargazers_count': 1469,
     'stargazers_url': f'https://api.github.com/repos/{user}/mock-repo/stargazers',
     'statuses_url': f'https://api.github.com/repos/{user}/mock-repo/statuses/{{sha}}',
     'subscribers_count': 86,
     'subscribers_url': f'https://api.github.com/repos/{user}/mock-repo/subscribers',
     'subscription_url': f'https://api.github.com/repos/{user}/mock-repo/subscription',
     'svn_url': f'https://github.com/{user}/mock-repo',
     'tags_url': f'https://api.github.com/repos/{user}/mock-repo/tags',
     'teams_url': f'https://api.github.com/repos/{user}/mock-repo/teams',
     'trees_url': f'https://api.github.com/repos/{user}/mock-repo/git/trees{{/sha}}',
     'updated_at': '2014-01-12T21:23:50Z',
     'url': f'https://api.github.com/repos/{user}/mock-repo',
     'watchers': 1469,
     'watchers_count': 1469,
     # NOTE: permissions are only available if authorized on the repo
     'permissions': { 'push': True }
     }))

    github_mock.branches.return_value = [
        Branch.from_json(dumps({'commit': {'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
           'url': f'https://api.github.com/repos/{user}/mock-repo/commits/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'},
          'name': 'dev'})),
         Branch.from_json(dumps({'commit': {'sha': '444a74d0d90a4aea744dacb31a14f87b5c30759c',
           'url': f'https://api.github.com/repos/{user}/mock-repo/commits/444a74d0d90a4aea744dacb31a14f87b5c30759c'},
          'name': 'master'})),
         Branch.from_json(dumps({'commit': {'sha': 'c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
           'url': f'https://api.github.com/repos/{user}/mock-repo/commits/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6'},
          'name': 'no-bundle'}))
      ]

    return github_mock
