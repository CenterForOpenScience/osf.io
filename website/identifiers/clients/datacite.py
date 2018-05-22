# -*- coding: utf-8 -*-
import re
import datetime

from website.util.client import BaseClient
from website import settings
from datacite import DataCiteMDSClient, schema40


class DataCiteClient(BaseClient):

    BASE_URL = settings.DATACITE_URL

    @property
    def _client(self):
        return DataCiteMDSClient(
            url=settings.DATACITE_URL,
            username=settings.DATACITE_USERNAME,
            password=settings.DATACITE_PASSWORD,
            prefix=settings.DATACITE_PREFIX
        )

    def build_doi(self, node):
        return settings.DOI_FORMAT.format(prefix=settings.DATACITE_PREFIX, guid=node._id)

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
                'resourceTypeGeneral': 'Dataset'
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

    def get_identifier(self, identifier):
        self._client.doi_get(identifier)

    def create_identifier(self, metadata, doi=None):
        resp = self._client.metadata_post(metadata)

        # Typical response: 'OK (10.5072/FK2osf.io/cq695)' to doi 10.5072/FK2osf.io/cq695
        doi = re.match(r'OK \((?P<doi>[a-zA-Z0-9 .\/]{0,})\)', resp).groupdict()['doi']
        return {'doi': doi}

    def change_status_identifier(self, status, metadata, identifier=None):
        return self.create_identifier(metadata)
