# -*- coding: utf-8 -*-

import pytest

from tests.utils import async
from tests.mocking import aiopretty, pypretty

import io
import os
import json
import base64
import asyncio

from waterbutler.providers import core
from waterbutler.providers.contrib.github import GithubProvider


@pytest.fixture
def auth():
    return {
        'name': 'cat',
        'email': 'cat@cat.com',
    }


@pytest.fixture
def identity():
    return {
        'owner': 'cat',
        'repo': 'food',
        'token': 'naps',
    }


@pytest.fixture
def provider(auth, identity):
    return GithubProvider(auth, identity)


@pytest.fixture
def file_content():
    return b'hungry'


@pytest.fixture
def file_like(file_content):
    return io.BytesIO(file_content)


@pytest.fixture
def file_wrapper(file_like):
    return core.FileWrapper(file_like)


@async
@pytest.mark.aiopretty
def test_download(provider):
    url = provider.build_repo_url('git', 'blobs', 'mysha')
    aiopretty.register_uri('GET', url, body=b'delicious')
    result = yield from provider.download('mysha')
    content = yield from result.response.read()
    assert content == b'delicious'


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


class TestGithubHelpers:

    def test_build_repo_url(self, identity, provider):
        expected = provider.build_url('repos', identity['owner'], identity['repo'], 'contents')
        assert provider.build_repo_url('contents') == expected

    def test_committer(self, auth, provider):
        expected = {
            'name': auth['name'],
            'email': auth['email'],
        }
        assert provider.committer == expected


@async
@pytest.mark.aiopretty
def test_metadata(provider, repo_contents):
    path = 'snacks'
    url = provider.build_repo_url('contents', path)
    aiopretty.register_uri('GET', url, body=json.dumps(repo_contents).encode('utf-8'), headers={'Content-Type': 'application/json'})
    result = yield from provider.metadata(path)
    assert result == [provider._serialize_metadata(item) for item in repo_contents]


@async
@pytest.mark.aiopretty
def test_upload_create(provider, repo_contents, file_content, file_wrapper):
    message = 'so hungry'
    path = repo_contents[0]['path'][::-1]
    metadata_url = provider.build_repo_url('contents', os.path.dirname(path))
    aiopretty.register_json_uri('GET', metadata_url, body=repo_contents)
    upload_url = provider.build_repo_url('contents', path)
    aiopretty.register_uri('PUT', upload_url)
    result = yield from provider.upload(file_wrapper, path, message)
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
def test_upload_update(provider, repo_contents, file_content, file_wrapper):
    path = repo_contents[0]['path']
    sha = repo_contents[0]['sha']
    message = 'so hungry'
    metadata_url = provider.build_repo_url('contents', os.path.dirname(path))
    aiopretty.register_json_uri('GET', metadata_url, body=repo_contents)
    upload_url = provider.build_repo_url('contents', path)
    aiopretty.register_uri('PUT', upload_url)
    result = yield from provider.upload(file_wrapper, path, message)
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
    result = yield from provider.delete(path, message, sha, branch=branch)
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
    result = yield from provider.delete(path, message, sha)
    expected_data = {
        'message': message,
        'sha': sha,
        'committer': provider.committer,
    }
    assert aiopretty.has_call(method='DELETE', uri=url, data=json.dumps(expected_data))
