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

    def build_url(self):
        return github3.session.GitHubSession().build_url(*args, **kwargs)

# TODO: allow changing the repo name
def create_mock_github(user='octo-cat', private=False):
    """Factory for mock GitHub objects.
    Example: ::

        >>> github = create_mock_github(user='octocat')
        >>> github.branches(user='octocat', repo='hello-world')
        >>> [{'commit': {'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
        ...   'url': 'https://api.github.com/repos/octocat/mock-repo/commits/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'},
        ...  'name': 'dev'},
        ... {'commit': {'sha': '444a74d0d90a4aea744dacb31a14f87b5c30759c',
        ...   'url': 'https://api.github.com/repos/octocat/mock-repo/commits/444a74d0d90a4aea744dacb31a14f87b5c30759c'},
        ...  'name': 'master'},
        ... {'commit': {'sha': 'c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
        ...   'url': 'https://api.github.com/repos/octocat/mock-repo/commits/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6'},
        ...  'name': 'no-bundle'}]

    :param str user: Github username.
    :param bool private: Whether repo is private.
    :return: An autospecced GitHub Mock object
    """
    github_mock = mock.create_autospec(GitHubClient)
    session = create_session_mock()

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
     'deployments_url': 'https://api.github.com/repos/{user}/mock-repo/deployments'.format(user=user),
     'created_at': '2013-06-30T18:29:18Z',
     'default_branch': 'dev',
     'description': 'Simple, Pythonic, text processing--Sentiment analysis, part-of-speech tagging, noun phrase extraction, translation, and more.',
     'downloads_url': 'https://api.github.com/repos/{user}/mock-repo/downloads'.format(user=user),
     'events_url': 'https://api.github.com/repos/{user}/mock-repo/events'.format(user=user),
     'fork': False,
     'forks': 89,
     'forks_count': 89,
     'forks_url': 'https://api.github.com/repos/{user}/mock-repo/forks',
     'full_name': '{user}/mock-repo'.format(user=user),
     'git_commits_url': 'https://api.github.com/repos/{user}/mock-repo/git/commits{{/sha}}'.format(user=user),
     'git_refs_url': 'https://api.github.com/repos/{user}/mock-repo/git/refs{{/sha}}'.format(user=user),
     'git_tags_url': 'https://api.github.com/repos/{user}/mock-repo/git/tags{{/sha}}'.format(user=user),
     'git_url': 'git://github.com/{user}/mock-repo.git'.format(user=user),
     'has_downloads': True,
     'archived': False,
     'has_issues': True,
     'has_pages': False,
     'has_projects': False,
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
     }), session)



    branch_1 = Branch.from_json(dumps({
        'commit': {
         'commit': {
          'author': {
           'name': 'Ian Cordasco',
           'email': '{user}@users.noreply.github.com',
           'date': '2015-06-19T22:37:18Z'
          },
          'committer': {
           'name': 'Ian Cordasco',
           'email': '{user}@users.noreply.github.com',
           'date': '2015-06-19T22:37:18Z'
          },
          'message': 'Merge pull request #388 from jonathanwcrane/patch-1\n\nCall out proper name of module in import statent',
          'tree': {
           'sha': '49d7464ad951e0e0e13bf073b06d8eed217c6e74',
           'url': 'https://api.github.com/repos/{user}/github3.py/git/trees/49d7464ad951e0e0e13bf073b06d8eed217c6e74'
          },
          'url': 'https://api.github.com/repos/{user}/github3.py/git/commits/749656b8b3b282d11a4221bb84e48291ca23ecc6',
          'comment_count': 0
         },
         'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230',
         'url': 'https://api.github.com/repos/{user}/mock-repo/commits/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'.format(user=user),
         'author': {
          'login': user,
          'id': 2379650,
          'avatar_url': 'https://avatars.githubusercontent.com/u/240830?v=3',
          'gravatar_id': '',
          'url': 'https://api.github.com/users/{user}'.format(user=user),
          'html_url': 'https://github.com/{user}'.format(user=user),
          'followers_url': 'https://api.github.com/users/{user}/followers'.format(user=user),
          'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}'.format(user=user),
          'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
          'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}'.format(user=user),
          'subscriptions_url': 'https://api.github.com/users/{user}/subscriptions'.format(user=user),
          'organizations_url': 'https://api.github.com/users/{user}/orgs'.format(user=user),
          'repos_url': 'https://api.github.com/users/{user}/repos'.format(user=user),
          'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}'.format(user=user),
          'received_events_url': 'https://api.github.com/users/{user}/received_events'.format(user=user),
          'type': 'User',
          'site_admin': False
         },
         'committer': {
          'login': user,
          'id': 240830,
          'avatar_url': 'https://avatars.githubusercontent.com/u/240830?v=3',
          'gravatar_id': '',
          'url': 'https://api.github.com/users/{user}'.format(user=user),
          'html_url': 'https://github.com/{user}'.format(user=user),
          'followers_url': 'https://api.github.com/users/{user}/followers'.format(user=user),
          'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}'.format(user=user),
          'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
          'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}'.format(user=user),
          'subscriptions_url': 'https://api.github.com/users/{user}/subscriptions'.format(user=user),
          'organizations_url': 'https://api.github.com/users/{user}/orgs'.format(user=user),
          'repos_url': 'https://api.github.com/users/{user}/repos'.format(user=user),
          'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}'.format(user=user),
          'received_events_url': 'https://api.github.com/users/{user}/received_events'.format(user=user),
          'type': 'User',
          'site_admin': False
         },
         'parents': [
          {
           'sha': 'b26841b7f083f9b7b3e3658fbc2fcc2e2f94db56',
           'url': 'https://api.github.com/repos/{user}/github3.py/commits/b26841b7f083f9b7b3e3658fbc2fcc2e2f94db56',
           'html_url': 'https://github.com/{user}/github3.py/commit/b26841b7f083f9b7b3e3658fbc2fcc2e2f94db56'
          }
         ],
         'url': 'https://api.github.com/repos/{user}/github3.py/commits/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'.format(user=user),
         'html_url': 'https://github.com/{user}/github3.py/commit/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'.format(user=user),
         'comments_url': 'https://api.github.com/repos/{user}/github3.py/commits/e22d92d5d90bb8f9695e9a5e2e2311a5c1997230/comments'.format(user=user)
        },
        '_links': {
         'self': 'https://api.github.com/repos/{user}/github3.py/branches/master',
         'html': 'https://github.com/{user}/github3.py/tree/master'
        },
        'protection': {
         'enabled': False,
          'required_status_checks': {
           'enforcement_level': 'off',
           'contexts': [
           ]
          }
        },
        'protected': False,
        'protection_url': 'https://api.github.com/repos/{user}/github3.py/branches/master/protection'.format(user=user),
        'name': 'dev'
    }), session)

    branch_2 = Branch.from_json(dumps({
        'commit': {
         'commit': {
          'author': {
           'name': 'Ian Cordasco',
           'email': '{user}@users.noreply.github.com',
           'date': '2015-06-19T22:37:18Z'
          },
          'committer': {
           'name': 'Ian Cordasco',
           'email': '{user}@users.noreply.github.com',
           'date': '2015-06-19T22:37:18Z'
          },
          'message': 'Merge pull request #388 from jonathanwcrane/patch-1\n\nCall out proper name of module in import statent',
          'tree': {
           'sha': '49d7464ad951e0e0e13bf073b06d8eed217c6e74',
           'url': 'https://api.github.com/repos/{user}/github3.py/git/trees/49d7464ad951e0e0e13bf073b06d8eed217c6e74'
          },
          'url': 'https://api.github.com/repos/{user}/github3.py/git/commits/749656b8b3b282d11a4221bb84e48291ca23ecc6',
          'comment_count': 0
         },
         'sha': '444a74d0d90a4aea744dacb31a14f87b5c30759c',
         'url': 'https://api.github.com/repos/{user}/mock-repo/commits/444a74d0d90a4aea744dacb31a14f87b5c30759c'.format(user=user),
         'author': {
          'login': user,
          'id': 2379650,
          'avatar_url': 'https://avatars.githubusercontent.com/u/240830?v=3',
          'gravatar_id': '',
          'url': 'https://api.github.com/users/{user}'.format(user=user),
          'html_url': 'https://github.com/{user}'.format(user=user),
          'followers_url': 'https://api.github.com/users/{user}/followers'.format(user=user),
          'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}'.format(user=user),
          'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
          'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}'.format(user=user),
          'subscriptions_url': 'https://api.github.com/users/{user}/subscriptions'.format(user=user),
          'organizations_url': 'https://api.github.com/users/{user}/orgs'.format(user=user),
          'repos_url': 'https://api.github.com/users/{user}/repos'.format(user=user),
          'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}'.format(user=user),
          'received_events_url': 'https://api.github.com/users/{user}/received_events'.format(user=user),
          'type': 'User',
          'site_admin': False
         },
         'committer': {
          'login': user,
          'id': 240830,
          'avatar_url': 'https://avatars.githubusercontent.com/u/240830?v=3',
          'gravatar_id': '',
          'url': 'https://api.github.com/users/{user}'.format(user=user),
          'html_url': 'https://github.com/{user}'.format(user=user),
          'followers_url': 'https://api.github.com/users/{user}/followers'.format(user=user),
          'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}'.format(user=user),
          'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
          'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}'.format(user=user),
          'subscriptions_url': 'https://api.github.com/users/{user}/subscriptions'.format(user=user),
          'organizations_url': 'https://api.github.com/users/{user}/orgs'.format(user=user),
          'repos_url': 'https://api.github.com/users/{user}/repos'.format(user=user),
          'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}'.format(user=user),
          'received_events_url': 'https://api.github.com/users/{user}/received_events'.format(user=user),
          'type': 'User',
          'site_admin': False
         },
         'parents': [
          {
           'sha': 'b26841b7f083f9b7b3e3658fbc2fcc2e2f94db56',
           'url': 'https://api.github.com/repos/{user}/github3.py/commits/b26841b7f083f9b7b3e3658fbc2fcc2e2f94db56',
           'html_url': 'https://github.com/{user}/github3.py/commit/b26841b7f083f9b7b3e3658fbc2fcc2e2f94db56'
          }
         ],
         'url': 'https://api.github.com/repos/{user}/github3.py/commits/444a74d0d90a4aea744dacb31a14f87b5c30759c'.format(user=user),
         'html_url': 'https://github.com/{user}/github3.py/commit/444a74d0d90a4aea744dacb31a14f87b5c30759c'.format(user=user),
         'comments_url': 'https://api.github.com/repos/{user}/github3.py/commits/444a74d0d90a4aea744dacb31a14f87b5c30759c/comments'.format(user=user)
        },
        '_links': {
         'self': 'https://api.github.com/repos/{user}/github3.py/branches/master',
         'html': 'https://github.com/{user}/github3.py/tree/master'
        },
        'protection': {
         'enabled': False,
          'required_status_checks': {
           'enforcement_level': 'off',
           'contexts': [
           ]
          }
        },
        'protected': False,
        'protection_url': 'https://api.github.com/repos/{user}/github3.py/branches/master/protection'.format(user=user),
        'name': 'master'
    }), session)

    branch_3 = Branch.from_json(dumps({
        'commit': {
         'commit': {
          'author': {
           'name': 'Ian Cordasco',
           'email': '{user}@users.noreply.github.com',
           'date': '2015-06-19T22:37:18Z'
          },
          'committer': {
           'name': 'Ian Cordasco',
           'email': '{user}@users.noreply.github.com',
           'date': '2015-06-19T22:37:18Z'
          },
          'message': 'Merge pull request #388 from jonathanwcrane/patch-1\n\nCall out proper name of module in import statent',
          'tree': {
           'sha': '49d7464ad951e0e0e13bf073b06d8eed217c6e74',
           'url': 'https://api.github.com/repos/{user}/github3.py/git/trees/49d7464ad951e0e0e13bf073b06d8eed217c6e74'
          },
          'url': 'https://api.github.com/repos/{user}/github3.py/git/commits/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
          'comment_count': 0
         },
         'sha': 'c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6',
         'url': 'https://api.github.com/repos/{user}/mock-repo/commits/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6'.format(user=user),
         'author': {
          'login': user,
          'id': 2379650,
          'avatar_url': 'https://avatars.githubusercontent.com/u/240830?v=3',
          'gravatar_id': '',
          'url': 'https://api.github.com/users/{user}'.format(user=user),
          'html_url': 'https://github.com/{user}'.format(user=user),
          'followers_url': 'https://api.github.com/users/{user}/followers'.format(user=user),
          'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}'.format(user=user),
          'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
          'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}'.format(user=user),
          'subscriptions_url': 'https://api.github.com/users/{user}/subscriptions'.format(user=user),
          'organizations_url': 'https://api.github.com/users/{user}/orgs'.format(user=user),
          'repos_url': 'https://api.github.com/users/{user}/repos'.format(user=user),
          'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}'.format(user=user),
          'received_events_url': 'https://api.github.com/users/{user}/received_events'.format(user=user),
          'type': 'User',
          'site_admin': False
         },
         'committer': {
          'login': user,
          'id': 240830,
          'avatar_url': 'https://avatars.githubusercontent.com/u/240830?v=3',
          'gravatar_id': '',
          'url': 'https://api.github.com/users/{user}'.format(user=user),
          'html_url': 'https://github.com/{user}'.format(user=user),
          'followers_url': 'https://api.github.com/users/{user}/followers'.format(user=user),
          'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}'.format(user=user),
          'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}'.format(user=user),
          'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}'.format(user=user),
          'subscriptions_url': 'https://api.github.com/users/{user}/subscriptions'.format(user=user),
          'organizations_url': 'https://api.github.com/users/{user}/orgs'.format(user=user),
          'repos_url': 'https://api.github.com/users/{user}/repos'.format(user=user),
          'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}'.format(user=user),
          'received_events_url': 'https://api.github.com/users/{user}/received_events'.format(user=user),
          'type': 'User',
          'site_admin': False
         },
         'parents': [
          {
           'sha': 'b26841b7f083f9b7b3e3658fbc2fcc2e2f94db56',
           'url': 'https://api.github.com/repos/{user}/github3.py/commits/b26841b7f083f9b7b3e3658fbc2fcc2e2f94db56',
           'html_url': 'https://github.com/{user}/github3.py/commit/b26841b7f083f9b7b3e3658fbc2fcc2e2f94db56'
          }
         ],
         'url': 'https://api.github.com/repos/{user}/github3.py/commits/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6'.format(user=user),
         'html_url': 'https://github.com/{user}/github3.py/commit/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6'.format(user=user),
         'comments_url': 'https://api.github.com/repos/{user}/github3.py/commits/c6eaaf6708561c3d4439c0c8dd99c2e33525b1e6/comments'.format(user=user)
        },
        '_links': {
         'self': 'https://api.github.com/repos/{user}/github3.py/branches/master',
         'html': 'https://github.com/{user}/github3.py/tree/master'
        },
        'protection': {
         'enabled': False,
          'required_status_checks': {
           'enforcement_level': 'off',
           'contexts': [
           ]
          }
        },
        'protected': False,
        'protection_url': 'https://api.github.com/repos/{user}/github3.py/branches/master/protection'.format(user=user),
        'name': '1.3.0'
    }), session)

    github_mock.branches.return_value =[branch_1, branch_2, branch_3]

    return github_mock

"""Below mock session functions come from github3.py library: tests.unit.helper.py"""

def get_build_url_proxy(*args, **kwargs):
    return github3.session.GitHubSession().build_url(*args, **kwargs)

def create_mocked_session():
    """Use mock to auto-spec a GitHubSession and return an instance."""
    MockedSession = mock.create_autospec(github3.session.GitHubSession)
    return MockedSession()

def create_session_mock(*args):
    """Create a mocked session and add headers and auth attributes."""
    session = create_mocked_session()
    base_attrs = ['headers', 'auth']
    attrs = dict(
        (key, mock.Mock()) for key in set(args).union(base_attrs)
    )
    session.configure_mock(**attrs)
    session.delete.return_value = None
    session.get.return_value = None
    session.patch.return_value = None
    session.post.return_value = None
    session.put.return_value = None
    session.has_auth.return_value = True
    session.build_url = get_build_url_proxy
    return session
