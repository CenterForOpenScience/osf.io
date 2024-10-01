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
from api.share.utils import shtrove_ingest_url, sharev2_push_url


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
                    # for legacy sharev2 support:
                    _rsps.add(responses.POST, sharev2_push_url(), status=200)
                    yield _rsps


@contextlib.contextmanager
def mock_update_share():
    with mock.patch.object(website_settings, 'SHARE_ENABLED', True):
        with mock.patch('api.share.utils._enqueue_update_share') as _mock_update_share:
            yield _mock_update_share


@contextlib.contextmanager
def expect_ingest_request(mock_share_responses, osfguid, *, token=None, delete=False, count=1, with_supplementary=True):
    mock_share_responses._calls.reset()
    yield
    _total_count = (
        count * 3  # (1) legacy (2) trove (3) trove supplementary
        if with_supplementary
        else count * 2
    )
    assert len(mock_share_responses.calls) == _total_count, (
        f'expected {_total_count} call(s), got {len(mock_share_responses.calls)}: {list(mock_share_responses.calls)}'
    )
    _trove_ingest_calls = []
    _trove_supp_ingest_calls = []
    _legacy_push_calls = []
    for _call in mock_share_responses.calls:
        if _call.request.url.startswith(shtrove_ingest_url()):
            if 'is_supplementary' in _call.request.url:
                _trove_supp_ingest_calls.append(_call)
            else:
                _trove_ingest_calls.append(_call)
        else:
            _legacy_push_calls.append(_call)
    assert len(_trove_ingest_calls) == count
    assert len(_trove_supp_ingest_calls) == (count if with_supplementary else 0)
    assert len(_legacy_push_calls) == count
    for _call in _trove_ingest_calls:
        assert_ingest_request(_call.request, osfguid, token=token, delete=delete)
    for _call in _trove_supp_ingest_calls:
        assert_ingest_request(_call.request, osfguid, token=token, delete=delete, supp=True)
    for _call in _legacy_push_calls:
        assert _call.request.url.startswith(sharev2_push_url())


def assert_ingest_request(request, expected_osfguid, *, token=None, delete=False, supp=False):
    _querydict = QueryDict(urlsplit(request.path_url).query)
    assert _querydict['record_identifier'] == (
        f'{expected_osfguid}/supplement' if supp else expected_osfguid
    )
    if delete:
        assert request.method == 'DELETE'
    else:
        assert request.method == 'POST'
        _focus_iri = _querydict['focus_iri']
        assert _focus_iri == f'{website_settings.DOMAIN}{expected_osfguid}'
        _request_body = request.body.decode('utf-8')
        assert (_focus_iri in _request_body) or (supp and not _request_body.strip())
    _token = token or website_settings.SHARE_API_TOKEN
    assert request.headers['Authorization'] == f'Bearer {_token}'


@contextlib.contextmanager
def expect_preprint_ingest_request(mock_share_responses, preprint, *, delete=False, count=1, with_supplementary=True):
    # same as expect_ingest_request, but with convenience for preprint specifics
    # and postcommit-task handling (so on_preprint_updated actually runs)
    with expect_ingest_request(
        mock_share_responses,
        preprint._id,
        token=preprint.provider.access_token,
        delete=delete,
        count=count,
        with_supplementary=with_supplementary,
    ):
        # clear out postcommit tasks from factories
        postcommit_queue().clear()
        postcommit_celery_queue().clear()
        yield
        _mock_request = mock.Mock()
        _mock_request.status_code = 200
        # run postcommit tasks (specifically care about on_preprint_updated)
        postcommit_after_request(_mock_request)
