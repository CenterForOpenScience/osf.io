import logging
import re

from datacite import DataCiteMDSClient
from django.core.exceptions import ImproperlyConfigured

from osf.metadata.tools import pls_gather_metadata_file, pls_gather_metadata_as_dict
from website.identifiers.clients.base import AbstractIdentifierClient
from website import settings

logger = logging.getLogger(__name__)


class DataCiteClient(AbstractIdentifierClient):

    def __init__(self, node):
        try:
            assert settings.DATACITE_URL and (getattr(node.provider, 'doi_prefix', None) or settings.DATACITE_PREFIX)
        except AssertionError:
            raise ImproperlyConfigured('OSF\'Datacite client\'s settings are not configured')

        self._client = DataCiteMDSClient(
            url=settings.DATACITE_URL,
            username=settings.DATACITE_USERNAME,
            password=settings.DATACITE_PASSWORD,
            prefix=getattr(node.provider, 'doi_prefix', None) or settings.DATACITE_PREFIX
        )

    def build_metadata(self, node, doi_value=None, as_xml=True):
        doi_value = doi_value or self._get_doi_value(node)
        if as_xml:
            metadata_file = pls_gather_metadata_file(
                osf_item=node,
                format_key='datacite-xml',
                serializer_config={'doi_value': doi_value},
            )
            return metadata_file.serialized_metadata
        else:
            return pls_gather_metadata_as_dict(
                osf_item=node,
                format_key='datacite-json',
                serializer_config={'doi_value': doi_value},
            )

    def build_doi(self, object):
        return settings.DOI_FORMAT.format(
            prefix=getattr(object.provider, 'doi_prefix', None) or settings.DATACITE_PREFIX,
            guid=object._id
        )

    def get_identifier(self, identifier):
        self._client.doi_get(identifier)

    def create_identifier(self, node, category, doi_value=None):
        if category != 'doi':
            raise NotImplementedError(f'Creating an identifier with category {category} is not supported')
        doi_value = doi_value or self._get_doi_value(node)
        metadata_record_xml = self.build_metadata(node, doi_value, as_xml=True)
        if settings.DATACITE_ENABLED:
            resp = self._client.metadata_post(metadata_record_xml)
            # Typical response: 'OK (10.70102/FK2osf.io/cq695)' to doi 10.70102/FK2osf.io/cq695
            doi = re.match(r'OK \((?P<doi>[a-zA-Z0-9 .\/]{0,})\)', resp).groupdict()['doi']
            self._client.doi_post(doi, node.absolute_url)
            return {'doi': doi, 'metadata': metadata_record_xml}
        else:
            logger.info('TEST ENV: DOI built but not minted')
        return {'doi': doi_value, 'metadata': metadata_record_xml}

    def update_identifier(self, node, category, doi_value=None):
        if category != 'doi':
            raise NotImplementedError(f'Updating metadata not supported for {category}')
        doi_value = doi_value or self._get_doi_value(node)

        # Reuse create logic to post updated metadata if the resource is still public
        if node.is_public and not node.deleted:
            return self.create_identifier(node, category, doi_value=doi_value)

        if settings.DATACITE_ENABLED:
            self._client.metadata_delete(doi_value)
        return {'doi': doi_value}

    def _get_doi_value(self, node):
        return node.get_identifier_value('doi') or self.build_doi(node)
