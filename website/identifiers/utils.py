# -*- coding: utf-8 -*-

import re
import furl

from framework.exceptions import HTTPError


from website import settings
from website.identifiers.metadata import datacite_metadata_for_node, datacite_metadata


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


def get_doi_and_node_for_object(target_object):
    from osf.models import PreprintService

    node = target_object
    host = 'osf.io'
    if isinstance(target_object, PreprintService):
        host = furl.furl(target_object.provider.external_url).host
        node = target_object.node

    doi = settings.EZID_FORMAT.format(namespace=settings.DOI_NAMESPACE, host=host, guid=target_object._id)

    return doi, node


def build_ezid_metadata(target_object):
    """Build metadata for submission to EZID using the DataCite profile. See
    http://ezid.cdlib.org/doc/apidoc.html for details.
    Moved from website/project/views/register.py for use by other modules
    """
    doi, node = get_doi_and_node_for_object(target_object)
    metadata = {
        '_target': target_object.absolute_url,
        'datacite': datacite_metadata_for_node(node=node, doi=doi)
    }
    return doi, metadata


def get_or_create_identifiers(target_object):
    """
    Note: ARKs include a leading slash. This is stripped here to avoid multiple
    consecutive slashes in internal URLs (e.g. /ids/ark/<ark>/). Frontend code
    that build ARK URLs is responsible for adding the leading slash.
    Moved from website/project/views/register.py for use by other modules
    """
    from website.identifiers.client import EzidClient

    doi, metadata = build_ezid_metadata(target_object)
    client = EzidClient(settings.EZID_USERNAME, settings.EZID_PASSWORD)
    try:
        resp = client.create_identifier(doi, metadata)
        return dict(
            [each.strip('/') for each in pair.strip().split(':')]
            for pair in resp['success'].split('|')
        )
    except HTTPError as error:
        if 'identifier already exists' not in error.message.lower():
            raise
        resp = client.get_identifier(doi)
        doi = resp['success']
        suffix = doi.strip(settings.DOI_NAMESPACE)
        return {
            'doi': doi.replace('doi:', ''),
            'ark': '{0}{1}'.format(settings.ARK_NAMESPACE.replace('ark:', ''), suffix),
        }
