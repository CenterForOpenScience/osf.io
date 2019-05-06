# -*- coding: utf-8 -*-

import re
import logging

from framework.exceptions import HTTPError
from website import settings

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
            for key, value in data.items()
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


def request_identifiers(target_object):
    """Request identifiers for the target object using the appropriate client.

    :param target_object: object to request identifiers for
    :return: dict with keys relating to the status of the identifier
                 response - response from the DOI client
                 already_exists - the DOI has already been registered with a client
                 only_doi - boolean; only include the DOI (and not the ARK) identifier
                            when processing this response in get_or_create_identifiers
    """
    from website.identifiers.clients import exceptions

    if not target_object.should_request_identifiers:
        return False

    client = target_object.get_doi_client()
    if not client:
        return
    doi = client.build_doi(target_object)
    already_exists = False
    only_doi = True
    try:
        identifiers = target_object.request_identifier(category='doi')
    except exceptions.IdentifierAlreadyExists:
        identifiers = client.get_identifier(doi)
        already_exists = True
        only_doi = False
    except exceptions.ClientResponseError as error:
        raise HTTPError(error.response.status_code)
    return {
        'doi': identifiers.get('doi'),
        'already_exists': already_exists,
        'only_doi': only_doi
    }


def parse_identifiers(doi_client_response):
    """
    Note: ARKs include a leading slash. This is stripped here to avoid multiple
    consecutive slashes in internal URLs (e.g. /ids/ark/<ark>/). Frontend code
    that build ARK URLs is responsible for adding the leading slash.
    Moved from website/project/views/register.py for use by other modules
    """
    resp = doi_client_response['response']
    exists = doi_client_response.get('already_exists', None)
    if exists:
        doi = resp['success']
        suffix = doi.strip(settings.EZID_DOI_NAMESPACE)
        return {
            'doi': doi.replace('doi:', ''),
            'ark': '{0}{1}'.format(settings.EZID_ARK_NAMESPACE.replace('ark:', ''), suffix),
        }
    else:
        return {'doi': resp['doi']}


def get_or_create_identifiers(target_object):
    """
    Note: ARKs include a leading slash. This is stripped here to avoid multiple
    consecutive slashes in internal URLs (e.g. /ids/ark/<ark>/). Frontend code
    that build ARK URLs is responsible for adding the leading slash.
    Moved from website/project/views/register.py for use by other modules
    """
    response_dict = request_identifiers(target_object)
    ark = target_object.get_identifier(category='ark')
    doi = response_dict['doi']
    if not doi:
        client = target_object.get_doi_client()
        doi = client.build_doi(target_object)
    response = {'doi': doi}
    if ark:
        response['ark'] = ark.value

    return response
