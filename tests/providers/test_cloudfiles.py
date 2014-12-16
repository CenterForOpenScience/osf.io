import pytest
from unittest import mock

from tests.utils import async
from tests.mocking import aiopretty

import io
import time
import hashlib

import aiohttp

from waterbutler import streams
from waterbutler.providers import core
from waterbutler.providers import exceptions
from waterbutler.providers.contrib import cloudfiles


@pytest.fixture
def auth():
    return {
        'name': 'cat',
        'email': 'cat@cat.com',
    }


@pytest.fixture
def identity():
    return {
        'username': 'prince',
        'token': 'revolutionary',
        'region': 'iad',
        'container': 'purple rain',
    }


@pytest.fixture
def provider(auth, identity):
    return cloudfiles.CloudFilesProvider(auth, identity)


@pytest.fixture
def auth_json():
    return {
        "access": {
            "serviceCatalog": [
                {
                    "name": "cloudFiles",
                    "type": "object-store",
                    "endpoints": [
                        {
                            "publicURL": "https://storage101.iad3.clouddrive.com/v1/MossoCloudFS_926294",
                            "internalURL": "https://snet-storage101.iad3.clouddrive.com/v1/MossoCloudFS_926294",
                            "region": "IAD",
                            "tenantId": "MossoCloudFS_926294"
                        },
                    ]
                }
            ],
            "token": {
                "RAX-AUTH:authenticatedBy": [
                    "APIKEY"
                ],
                "tenant": {
                    "name": "926294",
                    "id": "926294"
                },
                "id": "2322f6b2322f4dbfa69802baf50b0832",
                "expires": "2014-12-17T09:12:26.069Z"
            },
            "user": {
                "name": "osf-production",
                "roles": [
                    {
                        "name": "object-store:admin",
                        "id": "10000256",
                        "description": "Object Store Admin Role for Account User"
                    },
                    {
                        "name": "compute:default",
                        "description": "A Role that allows a user access to keystone Service methods",
                        "id": "6",
                        "tenantId": "926294"
                    },
                    {
                        "name": "object-store:default",
                        "description": "A Role that allows a user access to keystone Service methods",
                        "id": "5",
                        "tenantId": "MossoCloudFS_926294"
                    },
                    {
                        "name": "identity:default",
                        "id": "2",
                        "description": "Default Role."
                    }
                ],
                "id": "secret",
                "RAX-AUTH:defaultRegion": "IAD"
            }
        }
    }


@pytest.fixture
def endpoint(auth_json):
    return auth_json['access']['serviceCatalog'][0]['endpoints'][0]['publicURL']


@pytest.fixture
def temp_url_key():
    return 'temporary beret'


@pytest.fixture
def mock_auth(auth_json):
    aiopretty.register_json_uri(
        'POST',
        cloudfiles.AUTH_URL,
        body=auth_json,
    )


@pytest.fixture
def mock_temp_key(endpoint, temp_url_key):
    aiopretty.register_uri(
        'HEAD',
        endpoint,
        status=204,
        headers={'X-Account-Meta-Temp-URL-Key': temp_url_key},
    )


@pytest.fixture
def mock_time(monkeypatch):
    mock_time = mock.Mock()
    mock_time.return_value = 10
    monkeypatch.setattr(time, 'time', mock_time)


@async
@pytest.mark.aiopretty
def test_download(provider, mock_auth, mock_temp_key, mock_time):
    path = 'lets-go-crazy'
    body = b'dearly-beloved'
    yield from provider._ensure_connection()
    url = provider.generate_url(path)
    aiopretty.register_uri('GET', url, body=body)
    result = yield from provider.download(path)
    content = yield from result.response.read()
    assert content == body


@async
@pytest.mark.aiopretty
def test_download_accept_url(provider, mock_auth, mock_temp_key, mock_time):
    path = 'lets-go-crazy'
    body = b'dearly-beloved'
    yield from provider._ensure_connection()
    url = provider.generate_url(path)
    result = yield from provider.download(path, accept_url=True)
    assert result == url
    aiopretty.register_uri('GET', url, body=body)
    response = yield from aiohttp.request('GET', url)
    content = yield from response.read()
    assert content == body


# @async
# @pytest.mark.aiopretty
# def test_download_not_found(provider):
#     pass
