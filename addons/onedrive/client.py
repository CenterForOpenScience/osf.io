# -*- coding: utf-8 -*-
from framework.exceptions import HTTPError

from website.util.client import BaseClient
from addons.onedrive import settings
from addons.onedrive.settings import DEFAULT_ROOT_ID


class OneDriveClient(BaseClient):

    def __init__(self, access_token=None, drive_id=None):
        self.access_token = access_token
        self.drive_id = drive_id

    @property
    def _default_headers(self):
        if self.access_token:
            return {'Authorization': 'bearer {}'.format(self.access_token)}
        return {}

    @property
    def _drive_url(self):
        if self.drive_id is not None:
            return self._build_url(settings.ONEDRIVE_API_URL, 'drives', self.drive_id)
        return self._build_url(settings.ONEDRIVE_API_URL, 'drive')

    def folders(self, folder_id=None):
        """Get list of subfolders of the folder with id ``folder_id``

        API Docs:  https://docs.microsoft.com/en-us/graph/api/driveitem-list-children

        :param str folder_id: the id of the parent folder. defaults to ``None``
        :rtype: list
        :return: a list of metadata objects representing the child folders of ``folder_id``
        """

        if folder_id is None or folder_id == DEFAULT_ROOT_ID:
            url = self._build_url(self._drive_url, 'items', DEFAULT_ROOT_ID)
        else:
            url = self._build_url(self._drive_url, 'items', folder_id)
        url = url + '?$expand=children($filter=folder%20ne%20null)'

        resp = self._make_request(
            'GET',
            url,
            expects=(200, ),
            throws=HTTPError(401)
        )
        data = resp.json()
        res = data['children']

        next_url = data.get('children@odata.nextLink', None)
        while next_url is not None:
            next_resp = self._make_request(
                'GET',
                next_url,
                expects=(200, ),
                throws=HTTPError(401)
            )
            next_data = next_resp.json()
            res.extend(next_data['value'])
            next_url = next_data.get('@odata.nextLink', None)

        return res

    def user_info(self):
        """Get information about the token's owner.

        API Docs::

        https://docs.microsoft.com/en-us/graph/api/user-get

        :rtype: dict
        :return: a dict containing metadata about the token's owner.
        """
        return self._make_request(
            'GET',
            self._build_url(settings.ONEDRIVE_API_URL, 'me'),
            expects=(200, ),
            throws=HTTPError(401)
        ).json()
