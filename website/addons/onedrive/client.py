# -*- coding: utf-8 -*-
import logging

#import requests #TODO: remove this after determining onedrive connection issues w/make_request

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import InvalidGrantError

from framework.exceptions import HTTPError

from website.util.client import BaseClient
from website.addons.base import exceptions
from website.addons.onedrive import settings

logger = logging.getLogger(__name__)


class OneDriveAuthClient(BaseClient):

    def refresh(self, access_token, refresh_token):
        client = OAuth2Session(
            settings.ONEDRIVE_KEY,
            token={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': '-30',
            }
        )

        extra = {
            'client_id': settings.ONEDRIVE_KEY,
            'client_secret': settings.ONEDRIVE_SECRET,
        }

        try:
            return client.refresh_token(
                self._build_url(settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT),
                # ('love')
                **extra
            )
        except InvalidGrantError:
            raise exceptions.InvalidAuthError()

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

        logger.debug('folders::made it1')
        logger.debug('URLs:' + self._build_url(settings.ONEDRIVE_API_URL, 'drive/', folder_id, '/children/'))
        res = self._make_request(
            'GET',
            self._build_url(settings.ONEDRIVE_API_URL, 'drive/', folder_id, '/children/'),
            params={'filter': query},
            expects=(200, ),
            throws=HTTPError(401)
        )
        logger.debug('folder_id::' + repr(folder_id))
        logger.debug('res::' + repr(res))
        return res.json()['value']
