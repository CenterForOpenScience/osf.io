# -*- coding: utf-8 -*-

import re
import logging
import unicodedata

from framework.exceptions import HTTPError

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


def request_identifiers(target_object):
    """Request identifiers for the target object using the appropriate client.

    :param target_object: object to request identifiers for
    :return: dict with DOI
    """
    from website.identifiers.clients import exceptions

    if not target_object.should_request_identifiers:
        return False

    client = target_object.get_doi_client()
    if not client:
        return
    doi = client.build_doi(target_object)
    try:
        identifiers = target_object.request_identifier(category='doi')
    except exceptions.IdentifierAlreadyExists:
        identifiers = client.get_identifier(doi)
    except exceptions.ClientResponseError as error:
        raise HTTPError(error.response.status_code)
    return {
        'doi': identifiers.get('doi')
    }


def get_or_create_identifiers(target_object):
    """
    Note: ARKs include a leading slash. This is stripped here to avoid multiple
    consecutive slashes in internal URLs (e.g. /ids/ark/<ark>/). Frontend code
    that build ARK URLs is responsible for adding the leading slash.
    Moved from website/project/views/register.py for use by other modules
    """
    doi = request_identifiers(target_object)['doi']
    if not doi:
        client = target_object.get_doi_client()
        doi = client.build_doi(target_object)

    ark = target_object.get_identifier(category='ark')
    if ark:
        return {'doi': doi, 'ark': ark}

    return {'doi': doi}

# From https://stackoverflow.com/a/19016117
# lxml does not accept strings with control characters
def remove_control_characters(s):
    return ''.join(ch for ch in s if unicodedata.category(ch)[0] != 'C')
