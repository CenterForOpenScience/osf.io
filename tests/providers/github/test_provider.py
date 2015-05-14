import pytest

from tests.utils import async

import io
import os
import json
import base64
import hashlib

import aiohttpretty

from waterbutler.core import streams
from waterbutler.core import exceptions

from waterbutler.providers.github import GitHubProvider
from waterbutler.providers.github.provider import GitHubPath
from waterbutler.providers.github.metadata import GitHubRevision
from waterbutler.providers.github.metadata import GitHubFileContentMetadata
from waterbutler.providers.github.metadata import GitHubFolderContentMetadata
from waterbutler.providers.github.metadata import GitHubFileTreeMetadata
from waterbutler.providers.github.metadata import GitHubFolderTreeMetadata


@pytest.fixture
def auth():
    return {
        'name': 'cat',
        'email': 'cat@cat.com',
    }


@pytest.fixture
def credentials():
    return {'token': 'naps'}


@pytest.fixture
def settings():
    return {
        'owner': 'cat',
        'repo': 'food',
    }


@pytest.fixture
def provider(auth, credentials, settings):
    return GitHubProvider(auth, credentials, settings)


@pytest.fixture
def file_content():
    return b'hungry'


@pytest.fixture
def file_like(file_content):
    return io.BytesIO(file_content)


@pytest.fixture
def file_stream(file_like):
    return streams.FileStreamReader(file_like)


@pytest.fixture
def upload_response():
    return {
        "content": {
            "name": "hello.txt",
            "path": "notes/hello.txt",
            "sha": "95b966ae1c166bd92f8ae7d1c313e738c731dfc3",
            "size": 9,
            "url": "https://api.github.com/repos/octocat/Hello-World/contents/notes/hello.txt",
            "html_url": "https://github.com/octocat/Hello-World/blob/master/notes/hello.txt",
            "git_url": "https://api.github.com/repos/octocat/Hello-World/git/blobs/95b966ae1c166bd92f8ae7d1c313e738c731dfc3",
            "type": "file",
            "_links": {
                "self": "https://api.github.com/repos/octocat/Hello-World/contents/notes/hello.txt",
                "git": "https://api.github.com/repos/octocat/Hello-World/git/blobs/95b966ae1c166bd92f8ae7d1c313e738c731dfc3",
                "html": "https://github.com/octocat/Hello-World/blob/master/notes/hello.txt"
            }
        },
        "commit": {
            "sha": "7638417db6d59f3c431d3e1f261cc637155684cd",
            "url": "https://api.github.com/repos/octocat/Hello-World/git/commits/7638417db6d59f3c431d3e1f261cc637155684cd",
            "html_url": "https://github.com/octocat/Hello-World/git/commit/7638417db6d59f3c431d3e1f261cc637155684cd",
            "author": {
                "date": "2010-04-10T14:10:01-07:00",
                "name": "Scott Chacon",
                "email": "schacon@gmail.com"
            },
            "committer": {
                "date": "2010-04-10T14:10:01-07:00",
                "name": "Scott Chacon",
                "email": "schacon@gmail.com"
            },
            "message": "my commit message",
            "tree": {
                "url": "https://api.github.com/repos/octocat/Hello-World/git/trees/691272480426f78a0138979dd3ce63b77f706feb",
                "sha": "691272480426f78a0138979dd3ce63b77f706feb"
            },
            "parents": [
                {
                    "url": "https://api.github.com/repos/octocat/Hello-World/git/commits/1acc419d4d6a9ce985db7be48c6349a0475975b5",
                    "html_url": "https://github.com/octocat/Hello-World/git/commit/1acc419d4d6a9ce985db7be48c6349a0475975b5",
                    "sha": "1acc419d4d6a9ce985db7be48c6349a0475975b5"
                }
            ]
        }
    }


@pytest.fixture
def create_folder_response():
    return {
        "content": {
            "name": ".gitkeep",
            "path": "i/like/trains/.gitkeep",
            "sha": "95b966ae1c166bd92f8ae7d1c313e738c731dfc3",
            "size": 9,
            "url": "https://api.github.com/repos/octocat/Hello-World/contents/notes/hello.txt",
            "html_url": "https://github.com/octocat/Hello-World/blob/master/notes/hello.txt",
            "git_url": "https://api.github.com/repos/octocat/Hello-World/git/blobs/95b966ae1c166bd92f8ae7d1c313e738c731dfc3",
            "type": "file",
            "_links": {
                "self": "https://api.github.com/repos/octocat/Hello-World/contents/notes/hello.txt",
                "git": "https://api.github.com/repos/octocat/Hello-World/git/blobs/95b966ae1c166bd92f8ae7d1c313e738c731dfc3",
                "html": "https://github.com/octocat/Hello-World/blob/master/notes/hello.txt"
            }
        },
        "commit": {
            "sha": "7638417db6d59f3c431d3e1f261cc637155684cd",
            "url": "https://api.github.com/repos/octocat/Hello-World/git/commits/7638417db6d59f3c431d3e1f261cc637155684cd",
            "html_url": "https://github.com/octocat/Hello-World/git/commit/7638417db6d59f3c431d3e1f261cc637155684cd",
            "author": {
                "date": "2010-04-10T14:10:01-07:00",
                "name": "Scott Chacon",
                "email": "schacon@gmail.com"
            },
            "committer": {
                "date": "2010-04-10T14:10:01-07:00",
                "name": "Scott Chacon",
                "email": "schacon@gmail.com"
            },
            "message": "my commit message",
            "tree": {
                "url": "https://api.github.com/repos/octocat/Hello-World/git/trees/691272480426f78a0138979dd3ce63b77f706feb",
                "sha": "691272480426f78a0138979dd3ce63b77f706feb"
            },
            "parents": [
                {
                    "url": "https://api.github.com/repos/octocat/Hello-World/git/commits/1acc419d4d6a9ce985db7be48c6349a0475975b5",
                    "html_url": "https://github.com/octocat/Hello-World/git/commit/1acc419d4d6a9ce985db7be48c6349a0475975b5",
                    "sha": "1acc419d4d6a9ce985db7be48c6349a0475975b5"
                }
            ]
        }
    }


@pytest.fixture
def repo_metadata():
    return {
        'full_name': 'octocat/Hello-World',
        'permissions': {
            'push': False,
            'admin': False,
            'pull': True
        },
        'has_downloads': True,
        'notifications_url': 'https://api.github.com/repos/octocat/Hello-World/notifications{?since,all,participating}',
        'releases_url': 'https://api.github.com/repos/octocat/Hello-World/releases{/id}',
        'downloads_url': 'https://api.github.com/repos/octocat/Hello-World/downloads',
        'merges_url': 'https://api.github.com/repos/octocat/Hello-World/merges',
        'owner': {
            'avatar_url': 'https://avatars.githubusercontent.com/u/583231?v=3',
            'organizations_url': 'https://api.github.com/users/octocat/orgs',
            'type': 'User',
            'starred_url': 'https://api.github.com/users/octocat/starred{/owner}{/repo}',
            'url': 'https://api.github.com/users/octocat',
            'html_url': 'https://github.com/octocat',
            'received_events_url': 'https://api.github.com/users/octocat/received_events',
            'subscriptions_url': 'https://api.github.com/users/octocat/subscriptions',
            'site_admin': False,
            'gravatar_id': '',
            'repos_url': 'https://api.github.com/users/octocat/repos',
            'gists_url': 'https://api.github.com/users/octocat/gists{/gist_id}',
            'id': 583231,
            'events_url': 'https://api.github.com/users/octocat/events{/privacy}',
            'login': 'octocat',
            'following_url': 'https://api.github.com/users/octocat/following{/other_user}',
            'followers_url': 'https://api.github.com/users/octocat/followers'
        },
        'html_url': 'https://github.com/octocat/Hello-World',
        'comments_url': 'https://api.github.com/repos/octocat/Hello-World/comments{/number}',
        'git_url': 'git://github.com/octocat/Hello-World.git',
        'ssh_url': 'git@github.com:octocat/Hello-World.git',
        'language': None,
        'pulls_url': 'https://api.github.com/repos/octocat/Hello-World/pulls{/number}',
        'subscribers_count': 1850,
        'forks_count': 1085,
        'watchers_count': 1407,
        'id': 1296269,
        'keys_url': 'https://api.github.com/repos/octocat/Hello-World/keys{/key_id}',
        'default_branch': 'master',
        'stargazers_count': 1407,
        'tags_url': 'https://api.github.com/repos/octocat/Hello-World/tags',
        'clone_url': 'https://github.com/octocat/Hello-World.git',
        'homepage': '',
        'forks_url': 'https://api.github.com/repos/octocat/Hello-World/forks',
        'branches_url': 'https://api.github.com/repos/octocat/Hello-World/branches{/branch}',
        'url': 'https://api.github.com/repos/octocat/Hello-World',
        'contents_url': 'https://api.github.com/repos/octocat/Hello-World/contents/{+path}',
        'hooks_url': 'https://api.github.com/repos/octocat/Hello-World/hooks',
        'git_tags_url': 'https://api.github.com/repos/octocat/Hello-World/git/tags{/sha}',
        'statuses_url': 'https://api.github.com/repos/octocat/Hello-World/statuses/{sha}',
        'trees_url': 'https://api.github.com/repos/octocat/Hello-World/git/trees{/sha}',
        'contributors_url': 'https://api.github.com/repos/octocat/Hello-World/contributors',
        'open_issues': 126,
        'has_pages': False,
        'pushed_at': '2014-06-11T21:51:23Z',
        'network_count': 1085,
        'commits_url': 'https://api.github.com/repos/octocat/Hello-World/commits{/sha}',
        'git_commits_url': 'https://api.github.com/repos/octocat/Hello-World/git/commits{/sha}',
        'svn_url': 'https://github.com/octocat/Hello-World',
        'forks': 1085,
        'fork': False,
        'subscription_url': 'https://api.github.com/repos/octocat/Hello-World/subscription',
        'archive_url': 'https://api.github.com/repos/octocat/Hello-World/{archive_format}{/ref}',
        'subscribers_url': 'https://api.github.com/repos/octocat/Hello-World/subscribers',
        'description': 'This your first repo!',
        'blobs_url': 'https://api.github.com/repos/octocat/Hello-World/git/blobs{/sha}',
        'teams_url': 'https://api.github.com/repos/octocat/Hello-World/teams',
        'compare_url': 'https://api.github.com/repos/octocat/Hello-World/compare/{base}...{head}',
        'issues_url': 'https://api.github.com/repos/octocat/Hello-World/issues{/number}',
        'stargazers_url': 'https://api.github.com/repos/octocat/Hello-World/stargazers',
        'private': False,
        'created_at': '2011-01-26T19:01:12Z',
        'issue_comment_url': 'https://api.github.com/repos/octocat/Hello-World/issues/comments/{number}',
        'has_issues': True,
        'milestones_url': 'https://api.github.com/repos/octocat/Hello-World/milestones{/number}',
        'issue_events_url': 'https://api.github.com/repos/octocat/Hello-World/issues/events{/number}',
        'languages_url': 'https://api.github.com/repos/octocat/Hello-World/languages',
        'name': 'Hello-World',
        'mirror_url': None,
        'has_wiki': True,
        'updated_at': '2014-12-12T16:45:49Z',
        'watchers': 1407,
        'open_issues_count': 126,
        'labels_url': 'https://api.github.com/repos/octocat/Hello-World/labels{/name}',
        'collaborators_url': 'https://api.github.com/repos/octocat/Hello-World/collaborators{/collaborator}',
        'assignees_url': 'https://api.github.com/repos/octocat/Hello-World/assignees{/user}',
        'size': 558,
        'git_refs_url': 'https://api.github.com/repos/octocat/Hello-World/git/refs{/sha}',
        'events_url': 'https://api.github.com/repos/octocat/Hello-World/events'
    }


@pytest.fixture
def branch_metadata():
    return {
        'commit': {
            'html_url': 'https://github.com/octocat/Hello-World/commit/7fd1a60b01f91b314f59955a4e4d4e80d8edf11d',
            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/7fd1a60b01f91b314f59955a4e4d4e80d8edf11d',
            'committer': {
                'html_url': 'https://github.com/octocat',
                'login': 'octocat',
                'type': 'User',
                'gravatar_id': '',
                'avatar_url': 'https://avatars.githubusercontent.com/u/583231?v=3',
                'received_events_url': 'https://api.github.com/users/octocat/received_events',
                'id': 583231,
                'starred_url': 'https://api.github.com/users/octocat/starred{/owner}{/repo}',
                'subscriptions_url': 'https://api.github.com/users/octocat/subscriptions',
                'organizations_url': 'https://api.github.com/users/octocat/orgs',
                'url': 'https://api.github.com/users/octocat',
                'following_url': 'https://api.github.com/users/octocat/following{/other_user}',
                'followers_url': 'https://api.github.com/users/octocat/followers',
                'repos_url': 'https://api.github.com/users/octocat/repos',
                'events_url': 'https://api.github.com/users/octocat/events{/privacy}',
                'gists_url': 'https://api.github.com/users/octocat/gists{/gist_id}',
                'site_admin': False
            },
            'parents': [{
                            'html_url': 'https://github.com/octocat/Hello-World/commit/553c2077f0edc3d5dc5d17262f6aa498e69d6f8e',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/553c2077f0edc3d5dc5d17262f6aa498e69d6f8e',
                            'sha': '553c2077f0edc3d5dc5d17262f6aa498e69d6f8e'
                        }, {
                            'html_url': 'https://github.com/octocat/Hello-World/commit/762941318ee16e59dabbacb1b4049eec22f0d303',
                            'url': 'https://api.github.com/repos/octocat/Hello-World/commits/762941318ee16e59dabbacb1b4049eec22f0d303',
                            'sha': '762941318ee16e59dabbacb1b4049eec22f0d303'
                        }],
            'sha': '7fd1a60b01f91b314f59955a4e4d4e80d8edf11d',
            'author': {
                'html_url': 'https://github.com/octocat',
                'login': 'octocat',
                'type': 'User',
                'gravatar_id': '',
                'avatar_url': 'https://avatars.githubusercontent.com/u/583231?v=3',
                'received_events_url': 'https://api.github.com/users/octocat/received_events',
                'id': 583231,
                'starred_url': 'https://api.github.com/users/octocat/starred{/owner}{/repo}',
                'subscriptions_url': 'https://api.github.com/users/octocat/subscriptions',
                'organizations_url': 'https://api.github.com/users/octocat/orgs',
                'url': 'https://api.github.com/users/octocat',
                'following_url': 'https://api.github.com/users/octocat/following{/other_user}',
                'followers_url': 'https://api.github.com/users/octocat/followers',
                'repos_url': 'https://api.github.com/users/octocat/repos',
                'events_url': 'https://api.github.com/users/octocat/events{/privacy}',
                'gists_url': 'https://api.github.com/users/octocat/gists{/gist_id}',
                'site_admin': False
            },
            'comments_url': 'https://api.github.com/repos/octocat/Hello-World/commits/7fd1a60b01f91b314f59955a4e4d4e80d8edf11d/comments',
            'commit': {
                'url': 'https://api.github.com/repos/octocat/Hello-World/git/commits/7fd1a60b01f91b314f59955a4e4d4e80d8edf11d',
                'message': 'Merge pull request #6 from Spaceghost/patch-1\n\nNew line at end of file.',
                'committer': {
                    'email': 'octocat@nowhere.com',
                    'date': '2012-03-06T23:06:50Z',
                    'name': 'The Octocat'
                },
                'tree': {
                    'url': 'https://api.github.com/repos/octocat/Hello-World/git/trees/b4eecafa9be2f2006ce1b709d6857b07069b4608',
                    'sha': 'b4eecafa9be2f2006ce1b709d6857b07069b4608'
                },
                'comment_count': 51,
                'author': {
                    'email': 'octocat@nowhere.com',
                    'date': '2012-03-06T23:06:50Z',
                    'name': 'The Octocat'
                }
            }
        },
        '_links': {
            'html': 'https://github.com/octocat/Hello-World/tree/master',
            'self': 'https://api.github.com/repos/octocat/Hello-World/branches/master'
        },
        'name': 'master'
    }

@pytest.fixture
def content_repo_metadata_root():
    return [
        {
            'path': 'file.txt',
            'type': 'file',
            'html_url': 'https://github.com/icereval/test/blob/master/file.txt',
            'git_url': 'https://api.github.com/repos/icereval/test/git/blobs/e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            'url': 'https://api.github.com/repos/icereval/test/contents/file.txt?ref=master',
            'sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            '_links': {
                'git': 'https://api.github.com/repos/icereval/test/git/blobs/e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
                'self': 'https://api.github.com/repos/icereval/test/contents/file.txt?ref=master',
                'html': 'https://github.com/icereval/test/blob/master/file.txt'
            },
            'name': 'file.txt',
            'size': 0,
            'download_url': 'https://raw.githubusercontent.com/icereval/test/master/file.txt'
        }, {
            'path': 'level1',
            'type': 'dir',
            'html_url': 'https://github.com/icereval/test/tree/master/level1',
            'git_url': 'https://api.github.com/repos/icereval/test/git/trees/bc1087ebfe8354a684bf9f8b75517784143dde86',
            'url': 'https://api.github.com/repos/icereval/test/contents/level1?ref=master',
            'sha': 'bc1087ebfe8354a684bf9f8b75517784143dde86',
            '_links': {
                'git': 'https://api.github.com/repos/icereval/test/git/trees/bc1087ebfe8354a684bf9f8b75517784143dde86',
                'self': 'https://api.github.com/repos/icereval/test/contents/level1?ref=master',
                'html': 'https://github.com/icereval/test/tree/master/level1'
            },
            'name': 'level1',
            'size': 0,
            'download_url': None
        }, {
            'path': 'test.rst',
            'type': 'file',
            'html_url': 'https://github.com/icereval/test/blob/master/test.rst',
            'git_url': 'https://api.github.com/repos/icereval/test/git/blobs/ca39bcbf849231525ce9e775935fcb18ed477b5a',
            'url': 'https://api.github.com/repos/icereval/test/contents/test.rst?ref=master',
            'sha': 'ca39bcbf849231525ce9e775935fcb18ed477b5a',
            '_links': {
                'git': 'https://api.github.com/repos/icereval/test/git/blobs/ca39bcbf849231525ce9e775935fcb18ed477b5a',
                'self': 'https://api.github.com/repos/icereval/test/contents/test.rst?ref=master',
                'html': 'https://github.com/icereval/test/blob/master/test.rst'
            },
            'name': 'test.rst',
            'size': 190,
            'download_url': 'https://raw.githubusercontent.com/icereval/test/master/test.rst'
        }
    ]

@pytest.fixture
def content_repo_metadata_folder():
    return [
        {
            'path': 'level1/child.txt',
            'type': 'file',
            'html_url': 'https://github.com/icereval/test/blob/master/level1/child.txt',
            'git_url': 'https://api.github.com/repos/icereval/test/git/blobs/1935c84e2c8da577ea92b8b4346d1d2bb92ed96e',
            'url': 'https://api.github.com/repos/icereval/test/contents/level1/child.txt?ref=master',
            'sha': '1935c84e2c8da577ea92b8b4346d1d2bb92ed96e',
            '_links': {
                'git': 'https://api.github.com/repos/icereval/test/git/blobs/1935c84e2c8da577ea92b8b4346d1d2bb92ed96e',
                'self': 'https://api.github.com/repos/icereval/test/contents/level1/child.txt?ref=master',
                'html': 'https://github.com/icereval/test/blob/master/level1/child.txt'
            },
            'name': 'child.txt',
            'size': 0,
            'download_url': 'https://raw.githubusercontent.com/icereval/test/master/level1/child.txt'
        },
    ]

@pytest.fixture
def repo_tree_metadata_root():
    return {
        'tree': [
            {
                'url': 'https://api.github.com/repos/icereval/test/git/blobs/e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
                'size': 0,
                'type': 'blob',
                'path': 'file.txt',
                'mode': '100644',
                'sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391'
            },
            {
                'type': 'tree',
                'url': 'https://api.github.com/repos/icereval/test/git/trees/05353097666f449344b7f69036c70a52dc504088',
                'path': 'level1',
                'mode': '040000',
                'sha': '05353097666f449344b7f69036c70a52dc504088'
            },
            {
                'url': 'https://api.github.com/repos/icereval/test/git/blobs/ca39bcbf849231525ce9e775935fcb18ed477b5a',
                'size': 190,
                'type': 'blob',
                'path': 'test.rst',
                'mode': '100644',
                'sha': 'ca39bcbf849231525ce9e775935fcb18ed477b5a'
            }
        ],
        'url': 'https://api.github.com/repos/icereval/test/git/trees/cd83e4a08261a54f1c4630fbb1de34d1e48f0c8a',
        'truncated': False,
        'sha': 'cd83e4a08261a54f1c4630fbb1de34d1e48f0c8a'
    }

@pytest.fixture
def repo_tree_metadata_root_recursive():
    return {
        'tree': [
            {
                'url': 'https://api.github.com/repos/icereval/test/git/blobs/e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
                'size': 0,
                'type': 'blob',
                'path': 'file.txt',
                'mode': '100644',
                'sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391'
            },
            {
                'type': 'tree',
                'url': 'https://api.github.com/repos/icereval/test/git/trees/05353097666f449344b7f69036c70a52dc504088',
                'path': 'level1',
                'mode': '040000',
                'sha': '05353097666f449344b7f69036c70a52dc504088'
            },
            {
                'url': 'https://api.github.com/repos/icereval/test/git/blobs/ca39bcbf849231525ce9e775935fcb18ed477b5a',
                'size': 190,
                'type': 'blob',
                'path': 'test.rst',
                'mode': '100644',
                'sha': 'ca39bcbf849231525ce9e775935fcb18ed477b5a'
            },
            {
                'url': 'https://api.github.com/repos/icereval/test/git/blobs/1935c84e2c8da577ea92b8b4346d1d2bb92ed96e',
                'size': 0,
                'type': 'blob',
                'path': 'level1/child.txt',
                'mode': '100644',
                'sha': '1935c84e2c8da577ea92b8b4346d1d2bb92ed96e'
            }
        ],
        'url': 'https://api.github.com/repos/icereval/test/git/trees/cd83e4a08261a54f1c4630fbb1de34d1e48f0c8a',
        'truncated': False,
        'sha': 'cd83e4a08261a54f1c4630fbb1de34d1e48f0c8a'
    }


@pytest.fixture
def content_repo_metadata_root_file_txt():
    return {
        '_links': {
            'git': 'https://api.github.com/repos/icereval/test/git/blobs/e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
            'self': 'https://api.github.com/repos/icereval/test/contents/file.txt?ref=master',
            'html': 'https://github.com/icereval/test/blob/master/file.txt'
        },
        'content': '',
        'url': 'https://api.github.com/repos/icereval/test/contents/file.txt?ref=master',
        'html_url': 'https://github.com/icereval/test/blob/master/file.txt',
        'download_url': 'https://raw.githubusercontent.com/icereval/test/master/file.txt',
        'name': 'file.txt',
        'type': 'file',
        'sha': 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
        'encoding': 'base64',
        'git_url': 'https://api.github.com/repos/icereval/test/git/blobs/e69de29bb2d1d6434b8b29ae775ad8c2e48c5391',
        'path': 'file.txt',
        'size': 0
    }


class TestHelpers:

    def test_build_repo_url(self, provider, settings):
        expected = provider.build_url('repos', settings['owner'], settings['repo'], 'contents')
        assert provider.build_repo_url('contents') == expected

    def test_committer(self, auth, provider):
        expected = {
            'name': auth['name'],
            'email': auth['email'],
        }
        assert provider.committer == expected


class TestCRUD:

    @async
    @pytest.mark.aiohttpretty
    def test_download_by_file_sha(self, provider):
        ref = hashlib.sha1().hexdigest()
        url = provider.build_repo_url('git', 'blobs', ref)
        aiohttpretty.register_uri('GET', url, body=b'delicious')
        result = yield from provider.download('', fileSha=ref)
        content = yield from result.read()
        assert content == b'delicious'

    @async
    @pytest.mark.aiohttpretty
    def test_download_by_path(self, provider):
        path = GitHubPath('/my.file')
        url = provider.build_repo_url('contents', path.path)
        aiohttpretty.register_uri('GET', url, body=b'delicious')
        result = yield from provider.download(str(path))
        content = yield from result.read()
        assert content == b'delicious'

    @async
    @pytest.mark.aiohttpretty
    def test_download_by_path_ref_branch(self, provider):
        path = GitHubPath('/my.file')
        ref = 'other_branch'
        url = provider.build_repo_url('contents', path.path, ref=ref)
        aiohttpretty.register_uri('GET', url, body=b'delicious')
        result = yield from provider.download(str(path), ref=ref)
        content = yield from result.read()
        assert content == b'delicious'

    @async
    @pytest.mark.aiohttpretty
    def test_download_bad_status(self, provider):
        ref = hashlib.sha1().hexdigest()
        url = provider.build_repo_url('git', 'blobs', ref)
        aiohttpretty.register_uri('GET', url, body=b'delicious', status=418)
        with pytest.raises(exceptions.DownloadError):
            yield from provider.download('', fileSha=ref)

    # @async
    # @pytest.mark.aiohttpretty
    # def test_upload_create(self, provider, upload_response, file_content, file_stream):
    #     message = 'so hungry'
    #     path = upload_response['content']['path'][::-1]
    #     metadata_url = provider.build_repo_url('contents', os.path.dirname(path))
    #     aiohttpretty.register_json_uri('GET', metadata_url, body=[upload_response['content']], status=200)
    #     upload_url = provider.build_repo_url('contents', path)
    #     aiohttpretty.register_json_uri('PUT', upload_url, body=upload_response, status=201)
    #     yield from provider.upload(file_stream, path, message)
    #     expected_data = {
    #         'path': path,
    #         'message': message,
    #         'content': base64.b64encode(file_content).decode('utf-8'),
    #         'committer': provider.committer,
    #     }
    #     assert aiohttpretty.has_call(method='GET', uri=metadata_url)
    #     assert aiohttpretty.has_call(method='PUT', uri=upload_url, data=json.dumps(expected_data))
    #
    # @async
    # @pytest.mark.aiohttpretty
    # def test_upload_update(self, provider, upload_response, file_content, file_stream):
    #     message = 'so hungry'
    #     sha = upload_response['content']['sha']
    #     path = '/' + upload_response['content']['path']
    #
    #     upload_url = provider.build_repo_url('contents', provider.build_path(path))
    #     metadata_url = provider.build_repo_url('contents', os.path.dirname(path))
    #
    #     aiohttpretty.register_json_uri('PUT', upload_url, body=upload_response)
    #     aiohttpretty.register_json_uri('GET', metadata_url, body=[upload_response['content']])
    #
    #     yield from provider.upload(file_stream, path, message)
    #
    #     expected_data = {
    #         'path': path,
    #         'message': message,
    #         'content': base64.b64encode(file_content).decode('utf-8'),
    #         'committer': provider.committer,
    #         'sha': sha,
    #     }
    #
    #     assert aiohttpretty.has_call(method='GET', uri=metadata_url)
    #     assert aiohttpretty.has_call(method='PUT', uri=upload_url, data=json.dumps(expected_data))

    # @async
    # @pytest.mark.aiohttpretty
    # def test_delete_with_branch(self, provider, repo_contents):
    #     path = os.path.join('/', repo_contents[0]['path'])
    #     sha = repo_contents[0]['sha']
    #     branch = 'master'
    #     message = 'deleted'
    #     url = provider.build_repo_url('contents', path)
    #     aiohttpretty.register_json_uri('DELETE', url)
    #     yield from provider.delete(path, message, sha, branch=branch)
    #     expected_data = {
    #         'message': message,
    #         'sha': sha,
    #         'committer': provider.committer,
    #         'branch': branch,
    #     }
    #
    #     assert aiohttpretty.has_call(method='DELETE', uri=url, data=json.dumps(expected_data))
    #
    # @async
    # @pytest.mark.aiohttpretty
    # def test_delete_without_branch(self, provider, repo_contents):
    #     path = repo_contents[0]['path']
    #     sha = repo_contents[0]['sha']
    #     message = 'deleted'
    #     url = provider.build_repo_url('contents', path)
    #     aiohttpretty.register_json_uri('DELETE', url)
    #     yield from provider.delete(path, message, sha)
    #     expected_data = {
    #         'message': message,
    #         'sha': sha,
    #         'committer': provider.committer,
    #     }
    #
    #     assert aiohttpretty.has_call(method='DELETE', uri=url, data=json.dumps(expected_data))


class TestZip:
    @async
    @pytest.mark.aiohttpretty
    def test_download_folder_root(self,
                                  provider,
                                  content_repo_metadata_root,
                                  content_repo_metadata_folder,
                                  repo_metadata,
                                  branch_metadata,
                                  repo_tree_metadata_root_recursive):
        root_path = GitHubPath('/')
        url = provider.build_repo_url('contents', str(root_path))
        aiohttpretty.register_json_uri(
            'GET',
            url,
            body=content_repo_metadata_root
        )

        aiohttpretty.register_json_uri(
            'GET',
            provider.build_repo_url('contents', str(GitHubPath('/level1/'))),
            body=content_repo_metadata_folder,
        )
        aiohttpretty.register_json_uri(
            'GET',
            provider.build_repo_url(),
            body=repo_metadata,
        )
        aiohttpretty.register_json_uri(
            'GET',
            provider.build_repo_url('branches', 'master'),
            body=branch_metadata,
        )
        aiohttpretty.register_json_uri(
            'GET',
            provider.build_repo_url(
                'git',
                'trees',
                '{}?recursive=1'.format(
                    branch_metadata['commit']['commit']['tree']['sha']
                ),
            ).replace('%3F', '?'),
            body=repo_tree_metadata_root_recursive,
        )

        aiohttpretty.register_uri(
            'GET',
            provider.build_repo_url('contents', '/file.txt'),
            body=b'text',
            headers={'Content-Length': len(b'text')},
        )
        aiohttpretty.register_uri(
            'GET',
            provider.build_repo_url('contents', '/test.rst'),
            body=b'rest',
            headers={'Content-Length': len(b'rest')}
        )
        aiohttpretty.register_uri(
            'GET',
            provider.build_repo_url('contents', '/level1/child.txt'),
            body=b'child',
            headers={'Content-Length': len(b'child')}
        )

        result = yield from provider.zip(str(root_path))
        content = yield from result.read()

        import zipfile
        import io
        zip = zipfile.ZipFile(io.BytesIO(content))

        assert zip.testzip() is None

        assert zip.open('file.txt').read() == b'text'
        assert zip.open('test.rst').read() == b'rest'
        assert zip.open('level1/child.txt').read() == b'child'


class TestMetadata:

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_file(self, provider, content_repo_metadata_root_file_txt):
        path = GitHubPath('/file.txt')
        url = provider.build_repo_url('contents', path.path)
        aiohttpretty.register_json_uri('GET', url, body=content_repo_metadata_root_file_txt)
        result = yield from provider.metadata(str(path))

        assert result == GitHubFileContentMetadata(content_repo_metadata_root_file_txt).serialized()

    # TODO: Additional Tests
    # def test_metadata_root_file_txt_branch(self, provider, repo_metadata, branch_metadata, repo_metadata_root):
    # def test_metadata_root_file_txt_commit_sha(self, provider, repo_metadata, branch_metadata, repo_metadata_root):

    @async
    @pytest.mark.aiohttpretty
    def test_metadata_folder_root(self, provider, content_repo_metadata_root):
        path = GitHubPath('/')
        url = provider.build_repo_url('contents', path.path)
        aiohttpretty.register_json_uri('GET', url, body=content_repo_metadata_root)
        result = yield from provider.metadata(str(path))

        ret = []
        for item in content_repo_metadata_root:
            if item['type'] == 'dir':
                ret.append(GitHubFolderContentMetadata(item).serialized())
            else:
                ret.append(GitHubFileContentMetadata(item).serialized())

        assert result == ret

    # TODO: Additional Tests
    # def test_metadata_non_root_folder(self, provider, repo_metadata, branch_metadata, repo_metadata_root):
    # def test_metadata_non_root_folder_branch(self, provider, repo_metadata, branch_metadata, repo_metadata_root):
    # def test_metadata_non_root_folder_commit_sha(self, provider, repo_metadata, branch_metadata, repo_metadata_root):


class TestCreateFolder:

    @async
    @pytest.mark.aiohttpretty
    def test_errors_out(self, provider):
        path = GitHubPath('/Imarealboy/')
        url = provider.build_repo_url('contents', os.path.join(path.path, '.gitkeep'))

        aiohttpretty.register_uri('PUT', url, status=400)

        with pytest.raises(exceptions.CreateFolderError) as e:
            yield from provider.create_folder(str(path))

        assert e.value.code == 400

    @async
    @pytest.mark.aiohttpretty
    def test_must_be_folder(self, provider):
        path = GitHubPath('/Imarealboy')

        with pytest.raises(exceptions.CreateFolderError) as e:
            yield from provider.create_folder(str(path))

    @async
    @pytest.mark.aiohttpretty
    def test_already_exists(self, provider):
        path = GitHubPath('/Imarealboy/')
        url = provider.build_repo_url('contents', os.path.join(path.path, '.gitkeep'))

        aiohttpretty.register_json_uri('PUT', url, status=422, body={
            'message': 'Invalid request.\n\n"sha" wasn\'t supplied.'
        })

        with pytest.raises(exceptions.FolderNamingConflict) as e:
            yield from provider.create_folder(str(path))

        assert e.value.code == 409
        assert e.value.message == 'Cannot create folder "Imarealboy" because a file or folder already exists at path "/Imarealboy/"'

    @async
    @pytest.mark.aiohttpretty
    def test_raises_other_422(self, provider):
        path = GitHubPath('/Imarealboy/')
        url = provider.build_repo_url('contents', os.path.join(path.path, '.gitkeep'))

        aiohttpretty.register_json_uri('PUT', url, status=422, body={
            'message': 'github no likey'
        })

        with pytest.raises(exceptions.CreateFolderError) as e:
            yield from provider.create_folder(str(path))

        assert e.value.code == 422
        assert e.value.data == {'message': 'github no likey'}

    @async
    @pytest.mark.aiohttpretty
    def test_returns_metadata(self, provider, create_folder_response):
        path = GitHubPath('/i/like/trains/')
        url = provider.build_repo_url('contents', os.path.join(path.path, '.gitkeep'))

        aiohttpretty.register_json_uri('PUT', url, status=201, body=create_folder_response)

        metadata = yield from provider.create_folder(str(path))

        assert metadata['kind'] == 'folder'
        assert metadata['name'] == 'trains'
        assert metadata['path'] == '/i/like/trains/'
