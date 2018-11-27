# -*- coding: utf-8 -*-
import logging
import furl
import requests
import waffle

from osf import features
from website import settings
from website.identifiers import utils
from website.util.client import BaseClient
from website.identifiers.clients import DataCiteClient, exceptions

logger = logging.getLogger(__name__)


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

    def build_doi(self, object):
        return settings.DOI_FORMAT.format(prefix=self.prefix, guid=object._id)

    def get_identifier(self, identifier):
        resp = self._make_request(
            'GET',
            self._build_url('id', identifier),
            expects=(200, ),
        )
        return utils.from_anvl(resp.content.strip('\n'))

    def create_identifier(self, object, category):
        if not waffle.switch_is_active(features.EZID_SWITCH):
            logger.info('ezid waffle switch is off. Doing nothing...')
            return None
        if category in ['doi', 'ark']:
            metadata = self.build_metadata(object)
            doi = self.build_doi(object)
            resp = requests.request(
                'PUT',
                self._build_url('id', doi),
                data=utils.to_anvl(metadata or {}),
            )
            if resp.status_code != 201:
                if 'identifier already exists' in resp.content:
                    raise exceptions.IdentifierAlreadyExists()
                else:
                    raise exceptions.ClientResponseError(resp)
            resp = utils.from_anvl(resp.content)
            return dict(
                [each.strip('/') for each in pair.strip().split(':')]
                for pair in resp['success'].split('|')
            )
        else:
            raise NotImplementedError('Create identifier method is not supported for category {}'.format(category))

    def update_identifier(self, object, category):
        if not waffle.switch_is_active(features.EZID_SWITCH):
            logger.info('ezid waffle switch is off. Doing nothing...')
            return None
        metadata = self.build_metadata(object)
        status = self.get_status(object)
        metadata['_status'] = status
        identifier = self.build_doi(object)
        resp = self._make_request(
            'POST',
            self._build_url('id', identifier),
            data=utils.to_anvl(metadata or {}),
            expects=(200, ),
        )
        return utils.from_anvl(resp.content)

    def get_status(self, object):
        from osf.models import PreprintService

        if isinstance(object, PreprintService):
            status = 'public' if object.verified_publishable else 'unavailable'
        else:
            status = 'public' if object.is_public or not object.is_deleted else 'unavailable'
        return status
