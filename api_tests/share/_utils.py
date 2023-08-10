import contextlib
from urllib.parse import urlsplit

from django.http import QueryDict

from website import settings as website_settings


@contextlib.contextmanager
def expect_ingest_request(mock_share_responses, osfguid, *, token=None, delete=False, count=1):
    mock_share_responses._calls.reset()
    yield
    assert len(mock_share_responses.calls) == count
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
