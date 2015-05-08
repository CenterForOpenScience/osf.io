# -*- coding: utf-8 -*-

import os
import itertools

import furl
import requests

from framework.exceptions import HTTPError


class BaseClient(object):

    @property
    def _auth(self):
        return None

    @property
    def _default_headers(self):
        return {}

    def _make_request(self, method, url, params=None, **kwargs):
        expects = kwargs.pop('expects', None)
        throws = kwargs.pop('throws', None)

        kwargs['headers'] = self._build_headers(**kwargs.get('headers', {}))

        response = requests.request(method, url, params=params, auth=self._auth, **kwargs)
        if expects and response.status_code not in expects:
            raise throws if throws else HTTPError(response.status_code, message=response.content)

        return response

    def _build_headers(self, **kwargs):
        headers = self._default_headers
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
