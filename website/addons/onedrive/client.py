# -*- coding: utf-8 -*-
from framework.exceptions import HTTPError

from website.util.client import BaseClient
from website.addons.onedrive import settings


class OneDriveAuthClient(BaseClient):

    def user_info(self, access_token):
        return self._make_request(
            'GET',
            self._build_url(settings.MSLIVE_API_URL, 'me'),
            params={'access_token': access_token},
            expects=(200, ),
            throws=HTTPError(401)
        ).json()


class OneDriveClient(BaseClient):

    def __init__(self, access_token=None):
        self.access_token = access_token

    @property
    def _default_headers(self):
        if self.access_token:
            return {'Authorization': 'bearer {}'.format(self.access_token)}
        return {}

    def about(self):
        return self._make_request(
            'GET',
            self._build_url(settings.ONEDRIVE_API_URL, 'drive', 'v2', 'about', ),
            expects=(200, ),
            throws=HTTPError(401)
        ).json()

    def folders(self, folder_id='root/'):
        query = 'folder ne null'

        if folder_id != 'root':
            folder_id = "items/{}".format(folder_id)

        res = self._make_request(
            'GET',
            self._build_url(settings.ONEDRIVE_API_URL, 'drive/', folder_id, '/children/'),
            params={'filter': query},
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['value']
