import mock
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
        super(GitHubAddonTestCase, self).set_node_settings(settings)
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
     'archive_url': 'https://api.github.com/repos/{user}/mock-repo/{{archive_format}}{{/ref}}'.format(user=user),
     'assignees_url': 'https://api.github.com/repos/{user}/mock-repo/assignees{{/user}}'.format(user=user),
     'blobs_url': 'https://api.github.com/repos/{user}/mock-repo/git/blobs{{/sha}}'.format(user=user),
     'branches_url': 'https://api.github.com/repos/{user}/mock-repo/branches{{/bra.format(user=user)nch}}'.format(user=user),
     'clone_url': 'https://github.com/{user}/mock-repo.git'.format(user=user),
     'collaborators_url': 'https://api.github.com/repos/{user}/mock-repo/collaborators{{/collaborator}}'.format(user=user),
     'comments_url': 'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}'.format(user=user),
     'commits_url': 'https://api.github.com/repos/{user}/mock-repo/commits{{/sha}}'.format(user=user),
     'compare_url': 'https://api.github.com/repos/{user}/mock-repo/compare/{{base}}...{{head}}',
     'contents_url': 'https://api.github.com/repos/{user}/mock-repo/contents/{{+path}}'.format(user=user),
     'contributors_url': 'https://api.github.com/repos/{user}/mock-repo/contributors'.format(user=user),
     'created_at': '2013-06-30T18:29:18Z',
     'default_branch': 'dev',
     'description': 'Simple, Pythonic, text processing--Sentiment analysis, part-of-speech tagging, noun phrase extraction, translation, and more.',
     'downloads_url': 'https://api.github.com/repos/{user}/mock-repo/downloads'.format(user=user),
     'events_url': 'https://api.github.com/repos/{user}/mock-repo/events'.format(user=user),
     'fork': False,
     'forks': 89,
     'forks_count': 89,
     'forks_url': 'https://api.github.com/repos/{user}/mock-repo/forks',
     'full_name': '{user}/mock-repo',
     'git_commits_url': 'https://api.github.com/repos/{user}/mock-repo/git/commits{{/sha}}'.format(user=user),
     'git_refs_url': 'https://api.github.com/repos/{user}/mock-repo/git/refs{{/sha}}'.format(user=user),
     'git_tags_url': 'https://api.github.com/repos/{user}/mock-repo/git/tags{{/sha}}'.format(user=user),
     'git_url': 'git://github.com/{user}/mock-repo.git'.format(user=user),
     'has_downloads': True,
     'has_issues': True,
     'has_wiki': True,
     'homepage': 'https://mock-repo.readthedocs.org/',
     'hooks_url': 'https://api.github.com/repos/{user}/mock-repo/hooks'.format(user=user),
     'html_url': 'https://github.com/{user}/mock-repo'.format(user=user),
     'id': 11075275,
     'issue_comment_url': 'https://api.github.com/repos/{user}/mock-repo/issues/comments/{{number}}'.format(user=user),
     'issue_events_url': 'https://api.github.com/repos/{user}/mock-repo/issues/events{{/number}}'.format(user=user),
     'issues_url': 'https://api.github.com/repos/{user}/mock-repo/issues{{/number}}'.format(user=user),
     'keys_url': 'https://api.github.com/repos/{user}/mock-repo/keys{{/key_id}}'.format(user=user),
     'labels_url': 'https://api.github.com/repos/{user}/mock-repo/labels{{/name}}'.format(user=user),
     'language': 'Python',
     'languages_url': 'https://api.github.com/repos/{user}/mock-repo/languages'.format(user=user),
     'master_branch': 'dev',
     'merges_url': 'https://api.github.com/repos/{user}/mock-repo/merges'.format(user=user),
     'milestones_url': 'https://api.github.com/repos/{user}/mock-repo/milestones{{/number}}'.format(user=user),
     'mirror_url': None,
     'name': 'mock-repo',
     'network_count': 89,
     'notifications_url': 'https://api.github.com/repos/{user}/mock-repo/notifications{{?since,all,participating}}'.format(user=user),
     'open_issues': 2,
     'open_issues_count': 2,
     'owner': {'avatar_url': 'https://gravatar.com/avatar/c74f9cfd7776305a82ede0b765d65402?d=https%3A%2F%2Fidenticons.github.com%2F3959fe3bcd263a12c28ae86a66ec75ef.png&r=x',
      'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}'.format(user=user),
      'followers_url': 'https://api.github.com/users/{user}/followers'.format(user=user),
      'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}'.format(user=user),
      'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
      'gravatar_id': 'c74f9cfd7776305a82ede0b765d65402',
      'html_url': 'https://github.com/{user}'.format(user=user),
      'id': 2379650,
      'login': user,
      'organizations_url': 'https://api.github.com/users/{user}/orgs'.format(user=user),
      'received_events_url': 'https://api.github.com/users/{user}/received_events',
      'repos_url': 'https://api.github.com/users/{user}/repos'.format(user=user),
      'site_admin': False,
      'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}',
      'subscriptions_url': 'https://api.github.com/users/{user}/subscriptions'.format(user=user),
      'type': 'User',
      'url': 'https://api.github.com/users/{user}'.format(user=user)},
     'private': private,
     'pulls_url': 'https://api.github.com/repos/{user}/mock-repo/pulls{{/number}}'.format(user=user),
     'pushed_at': '2013-12-30T16:05:54Z',
     'releases_url': 'https://api.github.com/repos/{user}/mock-repo/releases{{/id}}'.format(user=user),
     'size': 8717,
     'ssh_url': 'git@github.com:{user}/mock-repo.git'.format(user=user),
     'stargazers_count': 1469,
     'stargazers_url': 'https://api.github.com/repos/{user}/mock-repo/stargazers'.format(user=user),
     'statuses_url': 'https://api.github.com/repos/{user}/mock-repo/statuses/{{sha}}'.format(user=user),
     'subscribers_count': 86,
     'subscribers_url': 'https://api.github.com/repos/{user}/mock-repo/subscribers'.format(user=user),
     'subscription_url': 'https://api.github.com/repos/{user}/mock-repo/subscription'.format(user=user),
     'svn_url': 'https://github.com/{user}/mock-repo'.format(user=user),
     'tags_url': 'https://api.github.com/repos/{user}/mock-repo/tags'.format(user=user),
     'teams_url': 'https://api.github.com/repos/{user}/mock-repo/teams'.format(user=user),
     'trees_url': 'https://api.github.com/repos/{user}/mock-repo/git/trees{{/sha}}'.format(user=user),
     'updated_at': '2014-01-12T21:23:50Z',
     'url': 'https://api.github.com/repos/{user}/mock-repo'.format(user=user),
     'watchers': 1469,
     'watchers_count': 1469,
     # NOTE: permissions are only available if authorized on the repo
     'permissions': { 'push': True }
     }))

    github_mock.branches.return_value = [
        Branch.from_json(dumps({'commit': {'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
           'url': 'https://api.github.com/repos/{user}/mock-repo/commits/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'.format(user=user)},
          'name': 'dev'})),
         Branch.from_json(dumps({'commit': {'sha': '444a74d0d90a4aea744dacb31a14f87b5c30759c',
           'url': 'https://api.github.com/repos/{user}/mock-repo/commits/444a74d0d90a4aea744dacb31a14f87b5c30759c'.format(user=user)},
          'name': 'master'})),
         Branch.from_json(dumps({'commit': {'sha': 'c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
           'url': 'https://api.github.com/repos/{user}/mock-repo/commits/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6'.format(user=user)},
          'name': 'no-bundle'}))
      ]

    return github_mock
