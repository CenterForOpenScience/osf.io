import mock
from json import dumps
import github3
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
        u'archive_url': u'https://api.github.com/repos/{user}/mock-repo/{{archive_format}}{{/ref}}'.format(user=user),
        u'assignees_url': u'https://api.github.com/repos/{user}/mock-repo/assignees{{/user}}'.format(user=user),
        u'blobs_url': u'https://api.github.com/repos/{user}/mock-repo/git/blobs{{/sha}}'.format(user=user),
        u'branches_url': u'https://api.github.com/repos/{user}/mock-repo/branches{{/bra.format(user=user)nch}}'.format(
            user=user),
        u'clone_url': u'https://github.com/{user}/mock-repo.git'.format(user=user),
        u'collaborators_url': u'https://api.github.com/repos/{user}/mock-repo/collaborators{{/collaborator}}'.format(
            user=user),
        u'comments_url': u'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}'.format(user=user),
        u'commits_url': u'https://api.github.com/repos/{user}/mock-repo/commits{{/sha}}'.format(user=user),
        u'compare_url': u'https://api.github.com/repos/{user}/mock-repo/compare/{{base}}...{{head}}',
        u'contents_url': u'https://api.github.com/repos/{user}/mock-repo/contents/{{+path}}'.format(user=user),
        u'contributors_url': u'https://api.github.com/repos/{user}/mock-repo/contributors'.format(user=user),
        u'created_at': u'2013-06-30T18:29:18Z',
        u'default_branch': u'dev',
        u'description': u'Simple, Pythonic, text processing--Sentiment analysis, part-of-speech tagging, noun phrase extraction, translation, and more.',
        u'downloads_url': u'https://api.github.com/repos/{user}/mock-repo/downloads'.format(user=user),
        u'events_url': u'https://api.github.com/repos/{user}/mock-repo/events'.format(user=user),
        u'fork': False,
        u'forks': 89,
        u'forks_count': 89,
        u'forks_url': u'https://api.github.com/repos/{user}/mock-repo/forks',
        u'full_name': u'{user}/mock-repo',
        u'git_commits_url': u'https://api.github.com/repos/{user}/mock-repo/git/commits{{/sha}}'.format(user=user),
        u'git_refs_url': u'https://api.github.com/repos/{user}/mock-repo/git/refs{{/sha}}'.format(user=user),
        u'git_tags_url': u'https://api.github.com/repos/{user}/mock-repo/git/tags{{/sha}}'.format(user=user),
        u'git_url': u'git://github.com/{user}/mock-repo.git'.format(user=user),
        u'has_downloads': True,
        u'has_issues': True,
        u'has_wiki': True,
        u'homepage': u'https://mock-repo.readthedocs.org/',
        u'hooks_url': u'https://api.github.com/repos/{user}/mock-repo/hooks'.format(user=user),
        u'html_url': u'https://github.com/{user}/mock-repo'.format(user=user),
        u'id': 11075275,
        u'issue_comment_url': u'https://api.github.com/repos/{user}/mock-repo/issues/comments/{{number}}'.format(
            user=user),
        u'issue_events_url': u'https://api.github.com/repos/{user}/mock-repo/issues/events{{/number}}'.format(
            user=user),
        u'issues_url': u'https://api.github.com/repos/{user}/mock-repo/issues{{/number}}'.format(user=user),
        u'keys_url': u'https://api.github.com/repos/{user}/mock-repo/keys{{/key_id}}'.format(user=user),
        u'labels_url': u'https://api.github.com/repos/{user}/mock-repo/labels{{/name}}'.format(user=user),
        u'language': u'Python',
        u'languages_url': u'https://api.github.com/repos/{user}/mock-repo/languages'.format(user=user),
        u'master_branch': u'dev',
        u'merges_url': u'https://api.github.com/repos/{user}/mock-repo/merges'.format(user=user),
        u'milestones_url': u'https://api.github.com/repos/{user}/mock-repo/milestones{{/number}}'.format(user=user),
        u'mirror_url': None,
        u'name': u'mock-repo',
        u'network_count': 89,
        u'notifications_url': u'https://api.github.com/repos/{user}/mock-repo/notifications{{?since,all,participating}}'.format(
            user=user),
        u'open_issues': 2,
        u'open_issues_count': 2,
        u'owner': {
            u'avatar_url': u'https://gravatar.com/avatar/c74f9cfd7776305a82ede0b765d65402?d=https%3A%2F%2Fidenticons.github.com%2F3959fe3bcd263a12c28ae86a66ec75ef.png&r=x',
            u'events_url': u'https://api.github.com/users/{user}/events{{/privacy}}'.format(user=user),
            u'followers_url': u'https://api.github.com/users/{user}/followers'.format(user=user),
            u'following_url': u'https://api.github.com/users/{user}/following{{/other_user}}'.format(user=user),
            u'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
            u'gravatar_id': u'c74f9cfd7776305a82ede0b765d65402',
            u'html_url': u'https://github.com/{user}'.format(user=user),
            u'id': 2379650,
            u'login': user,
            u'organizations_url': u'https://api.github.com/users/{user}/orgs'.format(user=user),
            u'received_events_url': u'https://api.github.com/users/{user}/received_events',
            u'repos_url': u'https://api.github.com/users/{user}/repos'.format(user=user),
            u'site_admin': False,
            u'starred_url': u'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}',
            u'subscriptions_url': u'https://api.github.com/users/{user}/subscriptions'.format(user=user),
            u'type': u'User',
            u'url': u'https://api.github.com/users/{user}'.format(user=user)},
        u'private': private,
        u'pulls_url': u'https://api.github.com/repos/{user}/mock-repo/pulls{{/number}}'.format(user=user),
        u'pushed_at': u'2013-12-30T16:05:54Z',
        u'releases_url': u'https://api.github.com/repos/{user}/mock-repo/releases{{/id}}'.format(user=user),
        u'size': 8717,
        u'ssh_url': u'git@github.com:{user}/mock-repo.git'.format(user=user),
        u'stargazers_count': 1469,
        u'stargazers_url': u'https://api.github.com/repos/{user}/mock-repo/stargazers'.format(user=user),
        u'statuses_url': u'https://api.github.com/repos/{user}/mock-repo/statuses/{{sha}}'.format(user=user),
        u'subscribers_count': 86,
        u'subscribers_url': u'https://api.github.com/repos/{user}/mock-repo/subscribers'.format(user=user),
        u'subscription_url': u'https://api.github.com/repos/{user}/mock-repo/subscription'.format(user=user),
        u'svn_url': u'https://github.com/{user}/mock-repo'.format(user=user),
        u'tags_url': u'https://api.github.com/repos/{user}/mock-repo/tags'.format(user=user),
        u'teams_url': u'https://api.github.com/repos/{user}/mock-repo/teams'.format(user=user),
        u'trees_url': u'https://api.github.com/repos/{user}/mock-repo/git/trees{{/sha}}'.format(user=user),
        u'updated_at': u'2014-01-12T21:23:50Z',
        u'url': u'https://api.github.com/repos/{user}/mock-repo'.format(user=user),
        u'watchers': 1469,
        u'watchers_count': 1469,
        # NOTE: permissions are only available if authorized on the repo
        'permissions': {'push': True},
        'deployments_url': 'https://api.github.com/deployment',
        'archived': {},
        'has_pages': False,
        'has_projects': False,
    }), GitHubSession())

    github_mock.branches.return_value = [
        Branch.from_json(
            dumps(
                {
                    'commit': {
                        'parents': [
                            'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                            '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'
                        ],
                        'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
                        'html_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                        'author': {
                            'avatar_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'following_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'followers_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'id': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'login': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'organizations_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'received_events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'repos_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'starred_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'type': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
                            'gravatar_id': u'c74f9cfd7776305a82ede0b765d65402',
                            'html_url': f'https://github.com/{user}',
                            'subscriptions_url': f'https://api.github.com/users/{user}/subscriptions',
                        },
                        'commit': {
                            'parents': [
                                'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                                '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'
                            ],
                            'ETag': {},
                            'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
                            'html_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'author': {},
                            'committer': {
                                'avatar_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'following_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'followers_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'name': 'test',
                                'id': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'login': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'organizations_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'received_events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'repos_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'starred_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'type': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
                                'html_url': f'https://github.com/{user}',
                                'gravatar_id': u'c74f9cfd7776305a82ede0b765d65402',
                                'subscriptions_url': f'https://api.github.com/users/{user}/subscriptions',
                            },
                            'message': 'test message',
                            'tree': {
                                'url': 'test.com',
                                'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'
                            }
                        },
                        'comments_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                        'url': f'https://api.github.com/repos/{user}/mock-repo/commits/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
                        'committer': {
                            'avatar_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'following_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'followers_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'name': 'test',
                            'id': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'login': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'organizations_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'received_events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'repos_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'starred_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'type': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
                            'html_url': f'https://github.com/{user}',
                            'subscriptions_url': f'https://api.github.com/users/{user}/subscriptions',
                            'gravatar_id': u'c74f9cfd7776305a82ede0b765d65402',
                        }
                    },
                    'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                    '_links': [],
                    'protected': False,
                    'protection': {},
                    'protection_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                    'name': 'dev',
                }
            ),
            GitHubSession()
        ),
        Branch.from_json(
            dumps(
                {
                    'commit': {
                        'parents': [
                            'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                            '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'
                        ],
                        'sha': '444a74d0d90a4aea744dacb31a14f87b5c30759c',
                        'html_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                        'author': {
                            'avatar_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'following_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'followers_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'id': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'login': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'organizations_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'received_events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'repos_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'starred_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'type': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
                            'html_url': f'https://github.com/{user}',
                            'subscriptions_url': f'https://api.github.com/users/{user}/subscriptions',
                            'gravatar_id': u'c74f9cfd7776305a82ede0b765d65402',
                        },
                        'commit': {
                            'parents': [
                                'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                                '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'
                            ],
                            'html_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'ETag': {},
                            'sha': u'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'author': {},
                            'committer': {
                                'avatar_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'name': 'test',
                                'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'following_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'followers_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'id': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'login': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'organizations_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'received_events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'repos_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'starred_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'type': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
                                'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'html_url': f'https://github.com/{user}',
                                'subscriptions_url': f'https://api.github.com/users/{user}/subscriptions',
                                'gravatar_id': u'c74f9cfd7776305a82ede0b765d65402',
                            },
                            'message': 'test message',
                            'tree': {
                                'url': 'test.com',
                                'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
                            }
                        },
                        'comments_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                        'url': f'https://api.github.com/repos/{user}/mock-repo/commits/444a74d0d90a4aea744dacb31a14f87b5c30759c',
                        'committer': {
                            'avatar_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'following_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'followers_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'name': 'test',
                            'id': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'login': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'organizations_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'received_events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
                            'repos_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'starred_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'type': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'html_url': f'https://github.com/{user}',
                            'subscriptions_url': f'https://api.github.com/users/{user}/subscriptions',
                            'gravatar_id': u'c74f9cfd7776305a82ede0b765d65402',
                        }
                    },
                    'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                    '_links': [],
                    'protected': False,
                    'protection': {},
                    'protection_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                    'name': 'master',
                }
            ),
            GitHubSession()
        ),
        Branch.from_json(
            dumps(
                {
                    'commit': {
                        'parents': [
                            'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                            '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'
                        ],
                        'html_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                        'sha': 'c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
                        'author': {
                            'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'avatar_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'following_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'followers_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'id': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'login': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'organizations_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'received_events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'repos_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'starred_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'type': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'html_url': f'https://github.com/{user}',
                            'subscriptions_url': f'https://api.github.com/users/{user}/subscriptions',
                            'gravatar_id': u'c74f9cfd7776305a82ede0b765d65402',
                            'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
                        },
                        'commit': {
                            'parents': [
                                'ab64bbdcc51b170d21588e5c5d391ee5c0c96dfd',
                                '4cffe90e0a41ad3f5190079d7c8f036bde29cbe6'
                            ],
                            'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
                            'html_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'ETag': {},
                            'sha': u'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'author': {},
                            'committer': {
                                'name': 'test',
                                'avatar_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'following_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'followers_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'id': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'login': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'organizations_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'received_events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'repos_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'starred_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'type': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                                'html_url': f'https://github.com/{user}',
                                'subscriptions_url': f'https://api.github.com/users/{user}/subscriptions',
                                'gravatar_id': u'c74f9cfd7776305a82ede0b765d65402',
                                'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
                            },
                            'message': 'test message',
                            'tree': {
                                'url': 'test.com',
                                'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'
                            },
                        },
                        'comments_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                        'url': f'https://api.github.com/repos/{user}/mock-repo/commits/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
                        'committer': {
                            'avatar_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'following_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'followers_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'name': 'test',
                            'id': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'login': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'organizations_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'received_events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'repos_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'starred_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'type': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                            'html_url': f'https://github.com/{user}',
                            'subscriptions_url': f'https://api.github.com/users/{user}/subscriptions',
                            'gravatar_id': u'c74f9cfd7776305a82ede0b765d65402',
                            'gists_url': u'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
                        },
                    },
                    'events_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                    '_links': [],
                    'protected': False,
                    'protection': {},
                    'protection_url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                    'name': 'no-bundle',
                }
            ), GitHubSession()
        )
    ]

    return github_mock
