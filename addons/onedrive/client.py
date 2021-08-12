# -*- coding: utf-8 -*-
from framework.exceptions import HTTPError

from website.util.client import BaseClient
from addons.onedrive import settings

import logging
logger = logging.getLogger(__name__)


class OneDriveClient(BaseClient):

    def __init__(self, access_token=None):
        self.access_token = access_token

    @property
    def _default_headers(self):
        if self.access_token:
            return {'Authorization': 'Bearer {}'.format(self.access_token)}
        return {}

    def folders(self, drive_id=None, folder_id=None):
        """Get list of subfolders of the folder with id ``folder_id``

        API Docs:  https://dev.onedrive.com/items/list.htm

        :param str folder_id: the id of the parent folder. defaults to ``None``
        :rtype: list
        :return: a list of metadata objects representing the child folders of ``folder_id``
        """

        if drive_id is None:
            raise Exception('drive_id is undefined, cannot proceed')

        folder_path_part = 'root' if folder_id is None else folder_id
        list_folder_url = self._build_url(settings.MSGRAPH_API_URL, 'drives', drive_id,
                                          'items', folder_path_part, 'children')
        resp = self._make_request(
            'GET',
            list_folder_url,
            headers=self._default_headers,
            params={'filter': 'folder ne null'},
            expects=(200, ),
            throws=HTTPError(401)
        )
        folder_list = resp.json()
        logger.debug('folder_list:({})'.format(folder_list))
        return folder_list['value']

    def user_info(self):
        """Given an access token, return information about the token's owner.

        API Docs::

        https://msdn.microsoft.com/en-us/library/hh826533.aspx#requesting_info_using_rest
        https://msdn.microsoft.com/en-us/library/hh243648.aspx#user

        :param str access_token: a valid Microsoft Live access token
        :rtype: dict
        :return: a dict containing metadata about the token's owner.
        """

        # get user properties from /me endpoint
        me_url = self._build_url(settings.MSGRAPH_API_URL, 'me')
        me_resp = self._make_request(
            'GET',
            me_url,
            headers=self._default_headers,
            expects=(200, ),
            throws=HTTPError(401)
        )
        me_data = me_resp.json()
        logger.debug('me_data:({})'.format(me_data))

        retval = {
            'id': me_data['id'],
            'name': me_data['displayName'],
            'link': '{}/users/{}'.format(settings.MSGRAPH_API_URL, me_data['id']),
            'mail': me_data['userPrincipalName'],
        }

        # get drive properties from /users/$user_id/drive endpoint
        drive_url = self._build_url(settings.MSGRAPH_API_URL, 'users', retval['id'], 'drive')
        drive_resp = self._make_request(
            'GET',
            drive_url,
            headers=self._default_headers,
            expects=(200, ),
            throws=HTTPError(401)
        )
        drive_data = drive_resp.json()
        logger.debug('drive_data:({})'.format(drive_data))
        retval['drive_id'] = drive_data['id']

        if drive_data['driveType'] == 'personal':
            retval['name'] = '{} - OneDrive Personal'.format(retval['mail'])
        else:
            # get site properties from /sites endpoint
            # site_url = self._build_url(settings.MSGRAPH_API_URL, 'sites', 'root')
            # site_resp = self._make_request(
            #     'GET',
            #     site_url,
            #     headers=self._default_headers,
            #     expects=(200, ),
            #     throws=HTTPError(401)
            # )
            # site_data = site_resp.json()
            # logger.debug('site_data:({})'.format(site_data))
            retval['name'] = '{} - {}'.format(retval['mail'], 'OneDrive for School or Business')

        logger.debug('retval:({})'.format(retval))
        return retval
