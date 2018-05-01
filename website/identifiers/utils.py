# -*- coding: utf-8 -*-

import re
import logging

from framework.exceptions import HTTPError
from website import settings
from website.identifiers.metadata import datacite_metadata_for_node, crossref_metadata_for_preprint

logger = logging.getLogger(__name__)

FIELD_SEPARATOR = '\n'
PAIR_SEPARATOR = ': '


def encode(match):
    return '%{:02x}'.format(ord(match.group()))


def decode(match):
    return chr(int(match.group().lstrip('%'), 16))


def escape(value):
    return re.sub(r'[%:\r\n]', encode, value)


def unescape(value):
    return re.sub(r'%[0-9A-Fa-f]{2}', decode, value)


def to_anvl(data):
    if isinstance(data, dict):
        return FIELD_SEPARATOR.join(
            PAIR_SEPARATOR.join([escape(key), escape(to_anvl(value))])
            for key, value in data.iteritems()
        )
    return data


def _field_from_anvl(raw):
    key, value = raw.split(PAIR_SEPARATOR)
    return [unescape(key), from_anvl(unescape(value))]


def from_anvl(data):
    if PAIR_SEPARATOR in data:
        return dict([
            _field_from_anvl(pair)
            for pair in data.split(FIELD_SEPARATOR)
        ])
    return data


def merge_dicts(*dicts):
    return dict(sum((each.items() for each in dicts), []))


def get_doi_and_metadata_for_object(target_object, **kwargs):
    from osf.models import PreprintService, PreprintProvider

    metadata_function = datacite_metadata_for_node
    namespace = settings.EZID_DOI_NAMESPACE
    if isinstance(target_object, PreprintService):
        metadata_function = crossref_metadata_for_preprint
        doi_prefix = target_object.provider.doi_prefix
        if not doi_prefix:
            doi_prefix = PreprintProvider.objects.get(_id='osf').doi_prefix
        namespace = doi_prefix
    doi = settings.DOI_FORMAT.format(namespace=namespace, guid=target_object._id)

    metadata = metadata_function(target_object, doi, **kwargs)

    return doi, metadata


def build_doi_metadata(target_object, **kwargs):
    """Build metadata for DOI submission to a DOI client.
    Moved from website/project/views/register.py for use by other modules
    """
    doi, doi_metadata = get_doi_and_metadata_for_object(target_object, **kwargs)
    metadata = {
        '_target': target_object.absolute_url,
        'doi_metadata': doi_metadata
    }
    return doi, metadata


def get_doi_client(target_object):
    from website.identifiers.client import EzidClient, CrossRefClient
    from osf.models import PreprintService

    if isinstance(target_object, PreprintService):
        return CrossRefClient(settings.CROSSREF_USERNAME, settings.CROSSREF_PASSWORD)

    return EzidClient(settings.EZID_USERNAME, settings.EZID_PASSWORD)


def request_identifiers(target_object):
    doi, metadata = build_doi_metadata(target_object)

    client = get_doi_client(target_object)
    already_exists = False
    only_doi = True
    try:
        resp = client.create_identifier(doi, metadata)
    except HTTPError as error:
        already_exists = True
        if 'identifier already exists' not in error.message.lower():
            raise
        resp = client.get_identifier(doi)
        only_doi = False
    return {
        'response': resp,
        'already_exists': already_exists,
        'only_doi': only_doi
    }


def parse_identifiers(ezid_response):
    """
    Note: ARKs include a leading slash. This is stripped here to avoid multiple
    consecutive slashes in internal URLs (e.g. /ids/ark/<ark>/). Frontend code
    that build ARK URLs is responsible for adding the leading slash.
    Moved from website/project/views/register.py for use by other modules
    """
    resp = ezid_response['response']
    exists = ezid_response['already_exists']

    if exists:
        doi = resp['success']
        suffix = doi.strip(settings.EZID_DOI_NAMESPACE)
        return {
            'doi': doi.replace('doi:', ''),
            'ark': '{0}{1}'.format(settings.EZID_ARK_NAMESPACE.replace('ark:', ''), suffix),
        }
    else:
        identifiers = dict(
            [each.strip('/') for each in pair.strip().split(':')]
            for pair in resp['success'].split('|')
        )
        return {'doi': identifiers['doi']}


def get_or_create_identifiers(target_object):
    """
    Note: ARKs include a leading slash. This is stripped here to avoid multiple
    consecutive slashes in internal URLs (e.g. /ids/ark/<ark>/). Frontend code
    that build ARK URLs is responsible for adding the leading slash.
    Moved from website/project/views/register.py for use by other modules
    """
    response_dict = request_identifiers(target_object)

    resp = response_dict['response']
    exists = response_dict['already_exists']
    only_doi = response_dict['only_doi']
    if exists:
        doi = resp['success']
        suffix = doi.strip(settings.EZID_DOI_NAMESPACE)
        if not only_doi:
            return {
                'doi': doi.replace('doi:', ''),
                'ark': '{0}{1}'.format(settings.EZID_ARK_NAMESPACE.replace('ark:', ''), suffix),
            }
        else:
            return {'doi': doi.replace('doi:', '')}
    else:
        identifiers = dict(
            [each.strip('/') for each in pair.strip().split(':')]
            for pair in resp['success'].split('|')
        )
        return {'doi': identifiers['doi']}
