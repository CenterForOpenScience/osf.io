# -*- coding: utf-8 -*-
import pytest

import mock

from addons.onedrive import settings
from addons.onedrive.client import OneDriveClient
from addons.onedrive.tests.utils import (raw_root_folder_response, raw_me_response,
                                         raw_user_personal_drive_response, dummy_user_info)


def test_headers():
    client = OneDriveClient(access_token='meowmix')
    assert(client._default_headers == {'Authorization': 'bearer meowmix'})


def test_folders():

    def _quack_wrap(client2, drive_id2):
        def _quack(method, url, headers, expects, throws):
            assert(method == 'GET')
            assert(client2._build_url(settings.ONEDRIVE_API_URL, 'drives', drive_id2, 'items') in url)

            mock_res = mock.Mock()
            mock_res.json = mock.Mock(return_value={'children': raw_root_folder_response})
            return mock_res

        return _quack

    drive_id = 'abcd'
    client = OneDriveClient(access_token='meowmix', drive_id=drive_id)
    with mock.patch.object(client, '_make_request', side_effect=_quack_wrap(client, drive_id)):
        retval = client.folders()
        assert(retval == raw_root_folder_response)


def test_folders_without_drive_id():

    def _quack_wrap(client2):
        def _quack(method, url, headers, expects, throws):
            assert(method == 'GET')
            assert(client2._build_url(settings.ONEDRIVE_API_URL, 'drive', 'items') in url)

            mock_res = mock.Mock()
            mock_res.json = mock.Mock(return_value={'children': raw_root_folder_response})
            return mock_res

        return _quack

    client = OneDriveClient(access_token='meowmix')
    with mock.patch.object(client, '_make_request', side_effect=_quack_wrap(client)):
        retval = client.folders()
        assert(retval == raw_root_folder_response)


def test_user_info_token():

    def _woof(method, url, headers, expects, throws):
        assert(method == 'GET')

        if url.endswith('/me'):
            mock_me_res = mock.Mock()
            mock_me_res.json = mock.Mock(return_value=raw_me_response)
            return mock_me_res
        elif url.endswith('/drive'):
            mock_drive_res = mock.Mock()
            mock_drive_res.json = mock.Mock(return_value=raw_user_personal_drive_response)
            return mock_drive_res

        raise Exception('failure to match url {}'.format(url))

    client = OneDriveClient(access_token='meowmix')
    with mock.patch.object(client, '_make_request', side_effect=_woof):
        retval = client.user_info()
        assert(retval == dummy_user_info)
