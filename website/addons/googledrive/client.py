import os
import itertools

import furl
import requests

from requests_oauthlib import OAuth2Session

from framework import exceptions

from website.util import api_url_for
from website.addons.googledrive import settings


class BaseClient(object):

    def __init__(self, base):
        self.base = base

    @property
    def default_headers(self):
        return {}

    def _make_request(self, method, segments, **kwargs):
        query = kwargs.pop('query', {})
        expects = kwargs.pop('expects', None)
        throws = kwargs.pop('throws', exceptions.HTTPError)

        url = self._build_url(*segments, **query)
        kwargs['headers'] = self._build_headers(**kwargs.get('headers', {}))

        response = requests.request(method, url, **kwargs)
        if expects and response.status_code not in expects:
            raise throws

        return response

    def _build_headers(self, **kwargs):
        headers = self.default_headers
        headers.update(kwargs)
        return {
            key: value
            for key, value in headers.items()
            if value is not None
        }

    def _build_url(self, *segments, **query):
        url = furl.furl(self.base)
        segments = filter(
            lambda segment: segment,
            map(
                lambda segment: segment.strip('/'),
                itertools.chain(url.path.segments, segments)
            )
        )
        url.path = os.path.join(*segments)
        url.args = query
        return url.url


class GoogleAuthClient(BaseClient):

    def __init__(self, token=None):
        super(GoogleAuthClient, self).__init__(settings.OAUTH_BASE_URL)

    def start(self):
        client = OAuth2Session(
            settings.CLIENT_ID,
            redirect_uri=api_url_for('googledrive_oauth_finish', _absolute=True),
            scope=settings.OAUTH_SCOPE
        )
        return client.authorization_url(
            self._build_url('auth'),
            access_type='offline',
            approval_prompt='force'
        )

    def finish(self, code):
        client = OAuth2Session(
            settings.CLIENT_ID,
            redirect_uri=api_url_for('googledrive_oauth_finish', _absolute=True),
        )
        return client.fetch_token(
            self._build_url('token'),
            client_secret=settings.CLIENT_SECRET,
            code=code
        )

    def refresh(self, token):
        client = OAuth2Session(
            settings.CLIENT_ID,
            token=token
        )
        extra = {
            'client_id': settings.CLIENT_ID,
            'client_secret': settings.CLIENT_SECRET,
        }
        return client.refresh_token(
            self._build_url('token'),
            **extra
        )

    def revoke(self, token):
        return self._make_request(
            'GET',
            ('revoke', ),
            query={'token': token},
            expects=(200, 400, ),
            throws=Exception
        )


class GoogleDriveClient(BaseClient):

    def __init__(self, token=None):
        super(GoogleDriveClient, self).__init__(settings.DRIVE_BASE_URL)
        self.token = token

    @property
    def default_headers(self):
        if self.token:
            return {'authorization': 'Bearer {}'.format(self.token)}
        return {}

    def about(self):
        return self._make_request(
            'GET',
            ('about', ),
            expects=(200, ),
            throws=Exception
        ).json()

    def folders(self, folder_id='root'):
        query = ' and '.join([
            "'{0}' in parents".format(folder_id),
            'trashed = false',
            "mimeType = 'application/vnd.google-apps.folder'",
        ])
        res = self._make_request(
            'GET',
            ('files', ),
            query={'q': query},
            expects=(200, ),
            throws=Exception
        )
        return res.json()['items']
