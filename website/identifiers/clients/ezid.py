# -*- coding: utf-8 -*-
import furl
from website.identifiers import utils
from website.util.client import BaseClient
from website.identifiers.clients import DataCiteClient


class EzidClient(BaseClient, DataCiteClient):
    """Inherits _make_request from BaseClient"""

    def _build_url(self, *segments, **query):
        url = furl.furl(self.base_url)
        url.path.segments.extend(segments)
        url.args.update(query)
        return url.url

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

    def create_identifier(self, metadata, doi):
        resp = self._make_request(
            'PUT',
            self._build_url('id', doi),
            data=utils.to_anvl(metadata or {}),
            expects=(201, ),
        )
        resp = utils.from_anvl(resp.content)
        return dict(
            [each.strip('/') for each in pair.strip().split(':')]
            for pair in resp['success'].split('|')
        )

    def change_status_identifier(self, status, identifier, metadata=None):
        metadata['_status'] = status
        resp = self._make_request(
            'POST',
            self._build_url('id', identifier),
            data=utils.to_anvl(metadata or {}),
            expects=(200, ),
        )
        return utils.from_anvl(resp.content)
