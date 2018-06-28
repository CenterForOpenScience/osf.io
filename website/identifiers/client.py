# -*- coding: utf-8 -*-

import logging

import furl
import waffle
from website.util.client import BaseClient

from . import utils
logger = logging.getLogger(__name__)

EZID_SWITCH = 'ezid'

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
        if not waffle.switch_is_active(EZID_SWITCH):
            logger.info('ezid waffle switch is off. Doing nothing...')
            return None
        resp = self._make_request(
            'PUT',
            self._build_url('id', identifier),
            data=utils.to_anvl(metadata or {}),
            expects=(201, ),
        )
        return utils.from_anvl(resp.content)

    def mint_identifier(self, shoulder, metadata=None):
        if not waffle.switch_is_active(EZID_SWITCH):
            logger.info('ezid waffle switch is off. Doing nothing...')
            return None
        resp = self._make_request(
            'POST',
            self._build_url('shoulder', shoulder),
            data=utils.to_anvl(metadata or {}),
            expects=(201, ),
        )
        return utils.from_anvl(resp.content)

    def change_status_identifier(self, status, identifier, metadata=None):
        if not waffle.switch_is_active(EZID_SWITCH):
            logger.info('ezid waffle switch is off. Doing nothing...')
            return None
        metadata['_status'] = status
        resp = self._make_request(
            'POST',
            self._build_url('id', identifier),
            data=utils.to_anvl(metadata or {}),
            expects=(200, ),
        )
        return utils.from_anvl(resp.content)
