import pytest

from tests.utils import async
from tests.mocking import aiopretty

import io
import os
import json
import base64

from waterbutler import streams
from waterbutler.providers import core
from waterbutler.providers import exceptions
from waterbutler.providers.contrib.github import GithubProvider, GithubMetadata


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
    return GithubProvider(auth, credentials, settings)


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
def repo_contents():
    return [
        {
            'type': 'file',
            'size': 625,
            'name': 'octokit.rb',
            'path': 'lib/octokit.rb',
            'sha': 'fff6fe3a23bf1c8ea0692b4a883af99bee26fd3b',
            'url': 'https://api.github.com/repos/pengwynn/octokit/contents/lib/octokit.rb',
            'git_url': 'https://api.github.com/repos/pengwynn/octokit/git/blobs/fff6fe3a23bf1c8ea0692b4a883af99bee26fd3b',
            'html_url': 'https://github.com/pengwynn/octokit/blob/master/lib/octokit.rb',
            '_links': {
                'self': 'https://api.github.com/repos/pengwynn/octokit/contents/lib/octokit.rb',
                'git': 'https://api.github.com/repos/pengwynn/octokit/git/blobs/fff6fe3a23bf1c8ea0692b4a883af99bee26fd3b',
                'html': 'https://github.com/pengwynn/octokit/blob/master/lib/octokit.rb',
            },
        },
        {
            'type': 'dir',
            'size': 0,
            'name': 'octokit',
            'path': 'lib/octokit',
            'sha': 'a84d88e7554fc1fa21bcbc4efae3c782a70d2b9d',
            'url': 'https://api.github.com/repos/pengwynn/octokit/contents/lib/octokit',
            'git_url': 'https://api.github.com/repos/pengwynn/octokit/git/trees/a84d88e7554fc1fa21bcbc4efae3c782a70d2b9d',
            'html_url': 'https://github.com/pengwynn/octokit/tree/master/lib/octokit',
            '_links': {
                'self': 'https://api.github.com/repos/pengwynn/octokit/contents/lib/octokit',
                'git': 'https://api.github.com/repos/pengwynn/octokit/git/trees/a84d88e7554fc1fa21bcbc4efae3c782a70d2b9d',
                'html': 'https://github.com/pengwynn/octokit/tree/master/lib/octokit',
            },
        },
    ]


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


class TestGithubHelpers:

    def test_build_repo_url(self, provider, settings):
        expected = provider.build_url('repos', settings['owner'], settings['repo'], 'contents')
        assert provider.build_repo_url('contents') == expected

    def test_committer(self, auth, provider):
        expected = {
            'name': auth['name'],
            'email': auth['email'],
        }
        assert provider.committer == expected


@async
@pytest.mark.aiopretty
def test_download(provider):
    url = provider.build_repo_url('git', 'blobs', 'mysha')
    aiopretty.register_uri('GET', url, body=b'delicious')
    result = yield from provider.download('mysha')
    content = yield from result.response.read()
    assert content == b'delicious'


@async
@pytest.mark.aiopretty
def test_download_bad_status(provider):
    url = provider.build_repo_url('git', 'blobs', 'mysha')
    aiopretty.register_uri('GET', url, body=b'delicious', status=418)
    with pytest.raises(exceptions.DownloadError):
        yield from provider.download('mysha')


@async
@pytest.mark.aiopretty
def test_metadata(provider, repo_contents):
    path = 'snacks'
    url = provider.build_repo_url('contents', path)
    aiopretty.register_json_uri('GET', url, body=repo_contents)
    result = yield from provider.metadata(path)
    assert result == [GithubMetadata(item).serialized() for item in repo_contents]


@async
@pytest.mark.aiopretty
def test_upload_create(provider, upload_response, file_content, file_stream):
    message = 'so hungry'
    path = upload_response['content']['path'][::-1]
    metadata_url = provider.build_repo_url('contents', os.path.dirname(path))
    aiopretty.register_json_uri('GET', metadata_url, body=[upload_response['content']], status=201)
    upload_url = provider.build_repo_url('contents', path)
    aiopretty.register_json_uri('PUT', upload_url, body=upload_response)
    yield from provider.upload(file_stream, path, message)
    expected_data = {
        'path': path,
        'message': message,
        'content': base64.b64encode(file_content).decode('utf-8'),
        'committer': provider.committer,
    }
    assert aiopretty.has_call(method='GET', uri=metadata_url)
    assert aiopretty.has_call(method='PUT', uri=upload_url, data=json.dumps(expected_data))


@async
@pytest.mark.aiopretty
def test_upload_update(provider, upload_response, file_content, file_stream):
    path = upload_response['content']['path']
    sha = upload_response['content']['sha']
    message = 'so hungry'
    metadata_url = provider.build_repo_url('contents', os.path.dirname(path))
    aiopretty.register_json_uri('GET', metadata_url, body=[upload_response['content']])
    upload_url = provider.build_repo_url('contents', path)
    aiopretty.register_json_uri('PUT', upload_url, body=upload_response)
    yield from provider.upload(file_stream, path, message)
    expected_data = {
        'path': path,
        'message': message,
        'content': base64.b64encode(file_content).decode('utf-8'),
        'committer': provider.committer,
        'sha': sha,
    }
    assert aiopretty.has_call(method='GET', uri=metadata_url)
    assert aiopretty.has_call(method='PUT', uri=upload_url, data=json.dumps(expected_data))


@async
@pytest.mark.aiopretty
def test_delete_with_branch(provider, repo_contents):
    path = repo_contents[0]['path']
    sha = repo_contents[0]['sha']
    branch = 'master'
    message = 'deleted'
    url = provider.build_repo_url('contents', path)
    aiopretty.register_json_uri('DELETE', url)
    yield from provider.delete(path, message, sha, branch=branch)
    expected_data = {
        'message': message,
        'sha': sha,
        'committer': provider.committer,
        'branch': branch,
    }
    assert aiopretty.has_call(method='DELETE', uri=url, data=json.dumps(expected_data))


@async
@pytest.mark.aiopretty
def test_delete_without_branch(provider, repo_contents):
    path = repo_contents[0]['path']
    sha = repo_contents[0]['sha']
    message = 'deleted'
    url = provider.build_repo_url('contents', path)
    aiopretty.register_json_uri('DELETE', url)
    yield from provider.delete(path, message, sha)
    expected_data = {
        'message': message,
        'sha': sha,
        'committer': provider.committer,
    }
    assert aiopretty.has_call(method='DELETE', uri=url, data=json.dumps(expected_data))
