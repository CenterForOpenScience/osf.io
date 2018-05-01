# -*- coding: utf-8 -*-

import furl
import requests
from framework.exceptions import HTTPError

from website.util.client import BaseClient
from website.settings import CROSSREF_DEPOSIT_URL

from . import utils


class EzidClient(BaseClient):

    BASE_URL = 'https://ezid.cdlib.org'

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def _build_url(self, *segments, **query):
        url = furl.furl(self.BASE_URL)
        url.path.segments.extend(segments)
        url.args.update(query)
        return url.url

    @property
    def _auth(self):
        return (self.username, self.password)

    @property
    def _default_headers(self):
        return {'Content-Type': 'text/plain; charset=UTF-8'}

    def get_identifier(self, identifier):
        resp = self._make_request(
            'GET',
            self._build_url('id', identifier),
            expects=(200, ),
        )
        return utils.from_anvl(resp.content.strip('\n'))

    def create_identifier(self, identifier, metadata=None):
        resp = self._make_request(
            'PUT',
            self._build_url('id', identifier),
            data=utils.to_anvl(metadata or {}),
            expects=(201, ),
        )
        return utils.from_anvl(resp.content)

    def mint_identifier(self, shoulder, metadata=None):
        resp = self._make_request(
            'POST',
            self._build_url('shoulder', shoulder),
            data=utils.to_anvl(metadata or {}),
            expects=(201, ),
        )
        return utils.from_anvl(resp.content)

    def change_status_identifier(self, status, identifier, metadata=None):
        metadata['_status'] = status
        resp = self._make_request(
            'POST',
            self._build_url('id', identifier),
            data=utils.to_anvl(metadata or {}),
            expects=(200, ),
        )
        return utils.from_anvl(resp.content)


class CrossRefClient(BaseClient):

    BASE_URL = CROSSREF_DEPOSIT_URL

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def _make_request(self, method, url, **kwargs):
        expects = kwargs.pop('expects', None)
        throws = kwargs.pop('throws', None)

        response = requests.request(method, url, **kwargs)
        if expects and response.status_code not in expects:
            raise throws if throws else HTTPError(response.status_code, message=response.content)

        return response

    def _build_url(self, **query):
        url = furl.furl(self.BASE_URL)
        url.args.update(query)
        return url.url

    def create_identifier(self, filename, metadata=None):
        resp = self._make_request(
            'POST',
            self._build_url(
                operation='doMDUpload',
                login_id=self.username,
                login_passwd=self.password,
                fname='{}.xml'.format(filename)
            ),
            files={'file': ('{}.xml'.format(filename), metadata['doi_metadata'])},
            expects=(200, ),
        )
        return resp

    def change_status_identifier(self, status, identifier, metadata=None):
        return self.create_identifier(identifier, metadata=metadata)
