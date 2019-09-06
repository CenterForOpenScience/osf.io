# -*- coding: utf-8 -*-
from __future__ import absolute_import
import logging

import re
import datetime

from website.identifiers.clients.base import AbstractIdentifierClient
from website import settings
from datacite import DataCiteMDSClient, schema40

logger = logging.getLogger(__name__)


class DataCiteClient(AbstractIdentifierClient):

    def __init__(self, base_url, prefix, client=None):
        self.base_url = base_url
        self.prefix = prefix
        self._client = client or DataCiteMDSClient(
            url=self.base_url,
            username=settings.DATACITE_USERNAME,
            password=settings.DATACITE_PASSWORD,
            prefix=self.prefix
        )

    def build_metadata(self, node):
        """Return the formatted datacite metadata XML as a string.
         """

        data = {
            'identifier': {
                'identifier': self.build_doi(node),
                'identifierType': 'DOI',
            },
            'creators': [
                {'creatorName': user.fullname,
                 'givenName': user.given_name,
                 'familyName': user.family_name} for user in node.visible_contributors
            ],
            'titles': [
                {'title': node.title}
            ],
            'publisher': 'Open Science Framework',
            'publicationYear': str(datetime.datetime.now().year),
            'resourceType': {
                'resourceType': 'Project',
                'resourceTypeGeneral': 'Text'
            }
        }

        if node.description:
            data['descriptions'] = [{
                'descriptionType': 'Abstract',
                'description': node.description
            }]

        if node.node_license:
            data['rightsList'] = [{
                'rights': node.node_license.name,
                'rightsURI': node.node_license.url
            }]

        # Validate dictionary
        assert schema40.validate(data)

        # Generate DataCite XML from dictionary.
        return schema40.tostring(data)

    def build_doi(self, object):
        return settings.DOI_FORMAT.format(prefix=self.prefix, guid=object._id)

    def get_identifier(self, identifier):
        self._client.doi_get(identifier)

    def create_identifier(self, node, category):
        if category == 'doi':
            metadata = self.build_metadata(node)
            resp = self._client.metadata_post(metadata)
            # Typical response: 'OK (10.70102/FK2osf.io/cq695)' to doi 10.70102/FK2osf.io/cq695
            doi = re.match(r'OK \((?P<doi>[a-zA-Z0-9 .\/]{0,})\)', resp).groupdict()['doi']
            if settings.DATACITE_MINT_DOIS:
                self._client.doi_post(doi, node.absolute_url)
            return {'doi': doi}
        else:
            raise NotImplementedError('Creating an identifier with category {} is not supported'.format(category))

    def update_identifier(self, node, category):
        if not node.is_public or node.is_deleted:
            if category == 'doi':
                doi = self.build_doi(node)
                self._client.metadata_delete(doi)
                return {'doi': doi}
            else:
                raise NotImplementedError('Updating metadata not supported for {}'.format(category))
        else:
            return self.create_identifier(node, category)
