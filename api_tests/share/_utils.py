import contextlib
from urllib.parse import urlsplit
from unittest import mock

from django.http import QueryDict
import responses

from framework.postcommit_tasks.handlers import (
    postcommit_after_request,
    postcommit_celery_queue,
    postcommit_queue,
)
from website import settings as website_settings
from api.share.utils import shtrove_ingest_url


@contextlib.contextmanager
def mock_share_responses():
    '''
    enable sending requests to shtrove with metadata updates,
    catch those requests in a yielded responses.RequestsMock
    '''
    with mock.patch.object(website_settings, 'SHARE_ENABLED', True):
        with mock.patch.object(website_settings, 'SHARE_API_TOKEN', 'mock-api-token'):
            with mock.patch.object(website_settings, 'USE_CELERY', False):  # run tasks synchronously
                with responses.RequestsMock(assert_all_requests_are_fired=False) as _rsps:
                    _ingest_url = shtrove_ingest_url()
                    _rsps.add(responses.POST, _ingest_url, status=200)
                    _rsps.add(responses.DELETE, _ingest_url, status=200)
                    yield _rsps


@contextlib.contextmanager
def mock_update_share():
    with mock.patch.object(website_settings, 'SHARE_ENABLED', True):
        with mock.patch('api.share.utils._enqueue_update_share') as _mock_update_share:
            yield _mock_update_share


@contextlib.contextmanager
def expect_ingest_request(mock_share_responses, osfguid, *, token=None, delete=False, count=1):
    mock_share_responses._calls.reset()
    yield
    assert len(mock_share_responses.calls) == count, (
        f'expected {count} call(s), got {len(mock_share_responses.calls)}: {list(mock_share_responses.calls)}'
    )
    for _call in mock_share_responses.calls:
        assert_ingest_request(_call.request, osfguid, token=token, delete=delete)


def assert_ingest_request(request, expected_osfguid, *, token=None, delete=False):
    _querydict = QueryDict(urlsplit(request.path_url).query)
    assert _querydict['record_identifier'] == expected_osfguid
    if delete:
        assert request.method == 'DELETE'
    else:
        assert request.method == 'POST'
        assert _querydict['focus_iri'] == f'{website_settings.DOMAIN}{expected_osfguid}'
    _token = token or website_settings.SHARE_API_TOKEN
    assert request.headers['Authorization'] == f'Bearer {_token}'


@contextlib.contextmanager
def expect_preprint_ingest_request(mock_share_responses, preprint, *, delete=False, count=1):
    # same as expect_ingest_request, but with convenience for preprint specifics
    # and postcommit-task handling (so on_preprint_updated actually runs)
    with expect_ingest_request(
        mock_share_responses,
        preprint._id,
        token=preprint.provider.access_token,
        delete=delete,
        count=count,
    ):
        # clear out postcommit tasks from factories
        postcommit_queue().clear()
        postcommit_celery_queue().clear()
        yield
        _mock_request = mock.Mock()
        _mock_request.status_code = 200
        # run postcommit tasks (specifically care about on_preprint_updated)
        postcommit_after_request(_mock_request)
