# -*- coding: utf-8 -*-
import json

from framework.exceptions import HTTPError

from website.util.client import BaseClient
from addons.iqbrims import settings


class IQBRIMSAuthClient(BaseClient):

    def userinfo(self, access_token):
        return self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'oauth2', 'v3', 'userinfo'),
            params={'access_token': access_token},
            expects=(200, ),
            throws=HTTPError(401)
        ).json()


class IQBRIMSClient(BaseClient):

    def __init__(self, access_token=None):
        self.access_token = access_token

    @property
    def _default_headers(self):
        if self.access_token:
            return {'authorization': 'Bearer {}'.format(self.access_token)}
        return {}

    def about(self):
        return self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'about', ),
            expects=(200, ),
            throws=HTTPError(401)
        ).json()

    def folders(self, folder_id='root'):
        query = ' and '.join([
            "'{0}' in parents".format(folder_id),
            'trashed = false',
            "mimeType = 'application/vnd.google-apps.folder'",
        ])
        res = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files', ),
            params={'q': query},
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['items']

    def create_folder(self, folder_id, title):
        res = self._make_request(
            'POST',
            self._build_url(settings.API_BASE_URL, 'drive', 'v2', 'files', ),
            headers={
                'Content-Type': 'application/json',
            },
            data=json.dumps({
                'title': title,
                'parents': [{
                    'id': folder_id
                }],
                'mimeType': 'application/vnd.google-apps.folder',
            }),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def create_folder_if_not_exists(self, folder_id, title):
        items = self.folders(folder_id)
        exists = filter(lambda item: item['title'] == title, items)

        if len(exists) > 0:
            return False, exists[0]
        else:
            return True, self.create_folder(folder_id, title)
