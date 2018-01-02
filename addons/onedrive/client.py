# -*- coding: utf-8 -*-
from framework.exceptions import HTTPError

from website.util.client import BaseClient
from addons.onedrive import settings
from addons.onedrive.settings import DEFAULT_ROOT_ID


class OneDriveClient(BaseClient):

    def __init__(self, access_token=None):
        self.access_token = access_token

    @property
    def _default_headers(self):
        if self.access_token:
            return {'Authorization': 'bearer {}'.format(self.access_token)}
        return {}

    def folders(self, folder_id=None):
        """Get list of subfolders of the folder with id ``folder_id``

        API Docs:  https://dev.onedrive.com/items/list.htm

        :param str folder_id: the id of the parent folder. defaults to ``None``
        :rtype: list
        :return: a list of metadata objects representing the child folders of ``folder_id``
        """

        if folder_id is None or folder_id == DEFAULT_ROOT_ID:
            url = self._build_url(settings.ONEDRIVE_API_URL, 'drive', DEFAULT_ROOT_ID, 'children')
        else:
            url = self._build_url(settings.ONEDRIVE_API_URL, 'drive', 'items',
                                  folder_id, 'children')

        res = self._make_request(
            'GET',
            url,
            params={'filter': 'folder ne null'},
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['value']

    def user_info_for_token(self, access_token):
        """Given an access token, return information about the token's owner.

        API Docs::

        https://msdn.microsoft.com/en-us/library/hh826533.aspx#requesting_info_using_rest
        https://msdn.microsoft.com/en-us/library/hh243648.aspx#user

        :param str access_token: a valid Microsoft Live access token
        :rtype: dict
        :return: a dict containing metadata about the token's owner.
        """
        return self._make_request(
            'GET',
            self._build_url(settings.MSLIVE_API_URL, 'me'),
            params={'access_token': access_token},
            expects=(200, ),
            throws=HTTPError(401)
        ).json()
