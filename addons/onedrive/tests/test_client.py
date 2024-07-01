import pytest

from unittest import mock

from addons.onedrive import settings
from addons.onedrive.client import OneDriveClient
from addons.onedrive.tests.utils import (raw_root_folder_response, raw_me_response,
                                         raw_user_personal_drive_response, dummy_user_info)


def test_headers():
    client = OneDriveClient(access_token='meowmix')
    assert (client._default_headers == {'Authorization': 'Bearer meowmix'})


def test_folders():

    def _quack(method, url, headers, params, expects, throws):
        if method != 'GET':
            raise 'failure to match method'

        if f'{settings.MSGRAPH_API_URL}/drives' not in url:
            raise 'failure to match url'

        mock_res = mock.Mock()
        mock_res.json = mock.Mock(return_value={'value': raw_root_folder_response})
        return mock_res

    client = OneDriveClient(access_token='meowmix')
    with mock.patch.object(client, '_make_request', side_effect=_quack):
        retval = client.folders(drive_id='abcd')
        assert (retval == raw_root_folder_response)


def test_user_info_token():

    def _woof(method, url, headers, expects, throws):
        if method != 'GET':
            raise 'failure to match method'

        if url.endswith('/me'):
            mock_me_res = mock.Mock()
            mock_me_res.json = mock.Mock(return_value=raw_me_response)
            return mock_me_res
        elif url.endswith('/drive'):
            mock_drive_res = mock.Mock()
            mock_drive_res.json = mock.Mock(return_value=raw_user_personal_drive_response)
            return mock_drive_res

        raise 'failure to match url'

    client = OneDriveClient(access_token='meowmix')
    with mock.patch.object(client, '_make_request', side_effect=_woof):
        retval = client.user_info()
        assert (retval == dummy_user_info)
