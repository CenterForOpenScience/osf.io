from unittest import mock
from json import dumps
import github3
from github3.repos import Repository
from github3.session import GitHubSession

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
    repo_author = {
        'name': f'{user}',
        'email': 'njqpw@osf.io',
        'avatar_url': 'https://gravatar.com/avatar/c74f9cfd7776305a82ede0b765d65402?d=https%3A%2F'
                      '%2Fidenticons.github.com%2F3959fe3bcd263a12c28ae86a66ec75ef.png&r=x',
        'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}',
        'followers_url': 'https://api.github.com/users/{user}/followers',
        'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}',
        'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}',
        'gravatar_id': 'c74f9cfd7776305a82ede0b765d65402',
        'html_url': 'https://github.com/{user}',
        'id': 2379650,
        'login': '{user}',
        'organizations_url': 'https://api.github.com/users/{user}/orgs',
        'received_events_url': 'https://api.github.com/users/{user}/received_events',
        'repos_url': 'https://api.github.com/users/{user}/repos',
        'site_admin': False,
        'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}',
        'subscriptions_url': 'https://api.github.com/users/{'
                             'user}/subscriptions',
        'type': 'User',
        'url': 'https://api.github.com/users/{user}'
    }

    repo_commit = {
        'ETag': '',
        'Last-Modified': '',
        'url': '',
        'author': repo_author,
        'committer': {'name': '{user}', 'email': '{user}@osf.io',
                      'username': 'tester'},
        'message': 'Fixed error',
        'tree': {'url': 'https://docs.github.com/en/rest/git/trees',
                 'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'},
    }

    repo_parents = [
        '12345',
        'https://api.example.com/entities/67890',
        'another-entity-id'
    ]

    repo_data = {
        'name': 'test',
        'id': '12345',
        'author': {'name': f'{user}', 'email': 'njqpw@osf.io'},
        'archive_url': 'https://api.github.com/repos/{user}/mock-repo/{{archive_format}}{{/ref}}',
        'assignees_url': 'https://api.github.com/repos/{user}/mock-repo/assignees{{/user}}',
        'blobs_url': 'https://api.github.com/repos/{user}/mock-repo/git/blobs{{/sha}}',
        'branches_url': 'https://api.github.com/repos/{user}/mock-repo/branches{{/bra.format(user=user)nch}}',
        'clone_url': 'https://github.com/{user}/mock-repo.git',
        'collaborators_url': 'https://api.github.com/repos/{user}/mock-repo/collaborators{{/collaborator}}',
        'comments_url': 'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}',
        'commits_url': 'https://api.github.com/repos/{user}/mock-repo/commits{{/sha}}',
        'compare_url': 'https://api.github.com/repos/{user}/mock-repo/compare/{{base}}...{{head}}',
        'contents_url': 'https://api.github.com/repos/{user}/mock-repo/contents/{{+path}}',
        'contributors_url': 'https://api.github.com/repos/{user}/mock-repo/contributors',
        'created_at': '2013-06-30T18:29:18Z',
        'default_branch': 'dev',
        'description': 'Simple, Pythonic, text processing--Sentiment analysis, part-of-speech tagging, '
                       'noun phrase extraction, translation, and more.',
        'downloads_url': 'https://api.github.com/repos/{user}/mock-repo/downloads',
        'events_url': 'https://api.github.com/repos/{user}/mock-repo/events',
        'fork': False,
        'forks': 89,
        'forks_count': 89,
        'forks_url': 'https://api.github.com/repos/{user}/mock-repo/forks',
        'full_name': '{user}/mock-repo',
        'git_commits_url': 'https://api.github.com/repos/{user}/mock-repo/git/commits{{/sha}}',
        'git_refs_url': 'https://api.github.com/repos/{user}/mock-repo/git/refs{{/sha}}',
        'git_tags_url': 'https://api.github.com/repos/{user}/mock-repo/git/tags{{/sha}}',
        'git_url': 'git://github.com/{user}/mock-repo.git',
        'has_downloads': True,
        'has_issues': True,
        'has_wiki': True,
        'homepage': 'https://mock-repo.readthedocs.org/',
        'hooks_url': 'https://api.github.com/repos/{user}/mock-repo/hooks',
        'html_url': 'https://github.com/{user}/mock-repo',
        'issue_comment_url': 'https://api.github.com/repos/{user}/mock-repo/issues/comments/{{number}}',
        'issue_events_url': 'https://api.github.com/repos/{user}/mock-repo/issues/events{{/number}}',
        'issues_url': 'https://api.github.com/repos/{user}/mock-repo/issues{{/number}}',
        'keys_url': 'https://api.github.com/repos/{user}/mock-repo/keys{{/key_id}}',
        'labels_url': 'https://api.github.com/repos/{user}/mock-repo/labels{{/name}}',
        'language': 'Python',
        'languages_url': 'https://api.github.com/repos/{user}/mock-repo/languages',
        'master_branch': 'dev',
        'merges_url': 'https://api.github.com/repos/{user}/mock-repo/merges',
        'milestones_url': 'https://api.github.com/repos/{user}/mock-repo/milestones{{/number}}',
        'mirror_url': None,
        'network_count': 89,
        'notifications_url': 'https://api.github.com/repos/{user}/mock-repo/notifications{{?since,all,'
                             'participating}}',
        'open_issues': 2,
        'open_issues_count': 2,
        'owner': repo_author,
        'private': '{private}',
        'pulls_url': 'https://api.github.com/repos/{user}/mock-repo/pulls{{/number}}',
        'pushed_at': '2013-12-30T16:05:54Z',
        'releases_url': 'https://api.github.com/repos/{user}/mock-repo/releases{{/id}}',
        'size': 8717,
        'ssh_url': 'git@github.com:{user}/mock-repo.git',
        'stargazers_count': 1469,
        'stargazers_url': 'https://api.github.com/repos/{user}/mock-repo/stargazers',
        'statuses_url': 'https://api.github.com/repos/{user}/mock-repo/statuses/{{sha}}',
        'subscribers_count': 86,
        'subscribers_url': 'https://api.github.com/repos/{user}/mock-repo/subscribers',
        'subscription_url': 'https://api.github.com/repos/{user}/mock-repo/subscription',
        'svn_url': 'https://github.com/{user}/mock-repo',
        'tags_url': 'https://api.github.com/repos/{user}/mock-repo/tags',
        'teams_url': 'https://api.github.com/repos/{user}/mock-repo/teams',
        'trees_url': 'https://api.github.com/repos/{user}/mock-repo/git/trees{{/sha}}',
        'updated_at': '2014-01-12T21:23:50Z',
        'url': 'https://api.github.com/repos/{user}/mock-repo',
        'watchers': 1469,
        'watchers_count': 1469,
        # NOTE: permissions are only available if authorized on the repo
        'permissions': {'push': True},
        'deployments_url': 'https://api.github.com/repos/{user}/{repo}/deployments',
        'archived': {},
        'has_pages': False,
        'has_projects': False,
    }
    github_mock = mock.create_autospec(GitHubClient)
    github_mock.repo.return_value = github3.repos.Repository.from_json(dumps(repo_data), GitHubSession())

    github_mock.branches.return_value = [
        Branch.from_json(dumps({
            'commit': {
                'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
                'url': f'https://api.github.com/repos/{user}/mock-repo/commits/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
                'author': repo_author,
                'comments_url': 'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}',
                'commit': repo_commit,
                'committer': repo_author,
                'html_url': 'https://github.com/{user}',
                'parents': repo_parents,
            },
            '_links': [{
                'rel': 'self',
                'href': 'https://api.example.com/entities/12345'
            }],
            'protected': True,
            'protection': 'public',
            'protection_url': 'https://api.example.com/docs/protection',
            'name': 'dev'},
        ),
            GitHubSession()),

        Branch.from_json(dumps({
            'commit': {
                'sha': '444a74d0d90a4aea744dacb31a14f87b5c30759c',
                'url': f'https://api.github.com/repos/{user}/mock-repo/commits'
                       f'/444a74d0d90a4aea744dacb31a14f87b5c30759c',
                'author': repo_author,
                'comments_url': 'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}',
                'commit': repo_commit,
                'committer': repo_author,
                'html_url': 'https://github.com/{user}',
                'parents': repo_parents,

            },
            '_links': [{
                'rel': 'self',
                'href': 'https://api.example.com/entities/12345'
            }],
            'protected': True,
            'protection': 'public',
            'protection_url': 'https://api.example.com/docs/protection',
            'name': 'master'}),
            GitHubSession()),

        Branch.from_json(dumps({
            'commit': {
                'sha': 'c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
                'url': f'https://api.github.com/repos/{user}/mock-repo/commits'
                       f'/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
                'author': repo_author,
                'comments_url': 'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}',
                'commit': repo_commit,
                'committer': repo_author,
                'html_url': 'https://github.com/{user}',
                'parents': repo_parents,

            },
            '_links': [{
                'rel': 'self',
                'href': 'https://api.example.com/entities/12345'
            }],
            'protected': True,
            'protection': 'public',
            'protection_url': 'https://api.example.com/docs/protection',
            'name': 'no-bundle'}),
            GitHubSession())
    ]

    return github_mock
