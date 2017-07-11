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

    @property
    def _default_params(self):
        return {}

    def _make_request(self, method, url, **kwargs):
        expects = kwargs.pop('expects', None)
        throws = kwargs.pop('throws', None)

        kwargs['headers'] = self._build_defaults(self._default_headers, **kwargs.get('headers', {}))
        kwargs['params'] = self._build_defaults(self._default_params, **kwargs.get('params', {}))

        response = requests.request(method, url, auth=self._auth, **kwargs)
        if expects and response.status_code not in expects:
            raise throws if throws else HTTPError(response.status_code, message=response.content)

        return response

    def _build_defaults(self, defaults, **kwargs):
        defaults.update(kwargs)
        return {
            key: value
            for key, value in defaults.items()
            if value is not None
        }

    def _build_url(self, base, *segments):
        url = furl.furl(base)
        segments = filter(
            lambda segment: segment,
            map(
                lambda segment: str(segment).strip('/'),
                itertools.chain(url.path.segments, segments)
            )
        )
        url.path = os.path.join(*segments)
        return url.url
