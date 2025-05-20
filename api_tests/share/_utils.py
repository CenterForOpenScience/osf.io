import contextlib
import re
from urllib.parse import urlsplit
from unittest import mock

from django.http import QueryDict
import responses

from framework.postcommit_tasks.handlers import (
    postcommit_after_request,
    postcommit_celery_queue,
    postcommit_queue,
)
from osf.models import Node, Preprint
from website import settings as website_settings, settings
from api.share.utils import shtrove_ingest_url
from osf.metadata.osf_gathering import OsfmapPartition


def gv_url():
    return fr'^{settings.GRAVYVALET_URL}/v1/configured-link-addons/\w*/verified-links'


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
                    _rsps.add(responses.GET, re.compile(gv_url()), status=200, body='{}')
                    yield _rsps


@contextlib.contextmanager
def mock_update_share():
    with mock.patch.object(website_settings, 'SHARE_ENABLED', True):
        with mock.patch('api.share.utils._enqueue_update_share') as _mock_update_share:
            yield _mock_update_share


@contextlib.contextmanager
def expect_ingest_request(mock_share_responses, item, *, token=None, delete=False, count=1, error_response=False):
    osfguid = item.get_guid()._id if isinstance(item, Preprint) else item._id
    mock_share_responses._calls.reset()
    yield
    _trove_main_count_per_item = 1
    expect_gv_call = isinstance(item, Node) and not delete
    _gv_calls_number = 1 if expect_gv_call else 0
    _trove_supplementary_count_per_item = (
        0
        if (error_response or delete)
        else (len(OsfmapPartition) - 1)
    )
    _total_count = count * (
        _trove_main_count_per_item
        + _trove_supplementary_count_per_item
        + _gv_calls_number
    )
    assert len(mock_share_responses.calls) == _total_count, (
        f'expected {_total_count} call(s), got {len(mock_share_responses.calls)}: {list(mock_share_responses.calls)}'
    )
    _trove_ingest_calls = []
    _trove_supp_ingest_calls = []
    _gv_links_calls = []
    for _call in mock_share_responses.calls:
        if _call.request.url.startswith(shtrove_ingest_url()):
            if 'is_supplementary' in _call.request.url:
                _trove_supp_ingest_calls.append(_call)
            else:
                _trove_ingest_calls.append(_call)
        elif _call.request.url.startswith(settings.GRAVYVALET_URL):
            _gv_links_calls.append(_call)
    assert len(_trove_ingest_calls) == count
    assert len(_trove_supp_ingest_calls) == count * _trove_supplementary_count_per_item
    assert len(_gv_links_calls) == (count if expect_gv_call else 0)
    for _call in _trove_ingest_calls:
        assert_ingest_request(_call.request, osfguid, token=token, delete=delete)
    for _call in _trove_supp_ingest_calls:
        assert_ingest_request(_call.request, osfguid, token=token, delete=delete, supp=True)


def assert_ingest_request(request, expected_osfguid, *, token=None, delete=False, supp=False):
    _querydict = QueryDict(urlsplit(request.path_url).query)
    if supp:
        assert _querydict['record_identifier'].startswith(expected_osfguid)
        assert _querydict['record_identifier'] != expected_osfguid
    else:
        assert _querydict['record_identifier'] == expected_osfguid
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
def expect_preprint_ingest_request(mock_share_responses, preprint, *, delete=False, count=1, error_response=False):
    # same as expect_ingest_request, but with convenience for preprint specifics
    # and postcommit-task handling (so on_preprint_updated actually runs)
    with expect_ingest_request(
        mock_share_responses,
        preprint,
        token=preprint.provider.access_token,
        delete=delete,
        count=count,
        error_response=error_response,
    ):
        # clear out postcommit tasks from factories
        postcommit_queue().clear()
        postcommit_celery_queue().clear()
        yield
        _mock_request = mock.Mock()
        _mock_request.status_code = 200
        # run postcommit tasks (specifically care about on_preprint_updated)
        postcommit_after_request(_mock_request)
