import os
import itertools

import furl
import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import InvalidGrantError

from framework.exceptions import HTTPError

from website.util import api_url_for
from website.addons.googledrive import settings
from website.addons.googledrive import exceptions


class BaseClient(object):

    @property
    def default_headers(self):
        return {}

    def _make_request(self, method, url, params=None, **kwargs):
        expects = kwargs.pop('expects', None)
        throws = kwargs.pop('throws', None)

        kwargs['headers'] = self._build_headers(**kwargs.get('headers', {}))

        response = requests.request(method, url, params=params, **kwargs)
        if expects and response.status_code not in expects:
            raise throws if throws else HTTPError(response.status_code)

        return response

    def _build_headers(self, **kwargs):
        headers = self.default_headers
        headers.update(kwargs)
        return {
            key: value
            for key, value in headers.items()
            if value is not None
        }

    def _build_url(self, base, *segments):
        url = furl.furl(base)
        segments = filter(
            lambda segment: segment,
            map(
                lambda segment: segment.strip('/'),
                itertools.chain(url.path.segments, segments)
            )
        )
        url.path = os.path.join(*segments)
        return url.url


class GoogleAuthClient(BaseClient):

    def start(self):
        client = OAuth2Session(
            settings.CLIENT_ID,
            redirect_uri=api_url_for('googledrive_oauth_finish', _absolute=True),
            scope=settings.OAUTH_SCOPE
        )
        return client.authorization_url(
            self._build_url(settings.OAUTH_BASE_URL, 'auth'),
            access_type='offline',
            approval_prompt='force'
        )

    def finish(self, code):
        client = OAuth2Session(
            settings.CLIENT_ID,
            redirect_uri=api_url_for('googledrive_oauth_finish', _absolute=True),
        )
        return client.fetch_token(
            self._build_url(settings.API_BASE_URL, 'oauth2', 'v3', 'token'),
            client_secret=settings.CLIENT_SECRET,
            code=code
        )

    def refresh(self, access_token, refresh_token):
        client = OAuth2Session(
            settings.CLIENT_ID,
            token={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': '-30',
            }
        )

        extra = {
            'client_id': settings.CLIENT_ID,
            'client_secret': settings.CLIENT_SECRET,
        }

        try:
            return client.refresh_token(
                self._build_url(settings.API_BASE_URL, 'oauth2', 'v3', 'token'),
                # ('love')
                **extra
            )
        except InvalidGrantError:
            raise exceptions.ExpiredAuthError()

    def userinfo(self, access_token):
        return self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'oauth2', 'v3', 'userinfo'),
            params={'access_token': access_token},
            expects=(200, ),
            throws=HTTPError(401)
        ).json()

    def revoke(self, token):
        return self._make_request(
            'GET',
            self._build_url(settings.OAUTH_BASE_URL, 'revoke'),
            params={'token': token},
            expects=(200, 400, ),
            throws=HTTPError(401)
        )


class GoogleDriveClient(BaseClient):

    def __init__(self, access_token=None):
        self.access_token = access_token

    @property
    def default_headers(self):
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
