'''for when you don't care about rdf or gatherbaskets, just want metadata about a thing.
'''
import typing

import requests
from website import settings as website_settings

from osf.models.base import coerce_guid
from osf.metadata.osf_gathering import pls_get_magic_metadata_basket, osf_iri
from osf.metadata.serializers import get_metadata_serializer


class SerializedMetadataFile(typing.NamedTuple):
    mediatype: str
    filename: str
    serialized_metadata: str


def pls_gather_metadata_as_dict(osf_item, format_key, serializer_config=None):
    '''for when you want metadata made of python primitives (e.g. a dictionary)

    @osf_item: the thing (osf model instance or 5-ish character guid string)
    @format_key: str (must be known by osf.metadata.serializers)
    @serializer_config: optional dict (use only when you know the serializer will understand)
    '''
    osfguid = coerce_guid(osf_item, create_if_needed=True)
    basket = pls_get_magic_metadata_basket(osfguid.referent)
    serializer = get_metadata_serializer(format_key, basket, serializer_config)
    return serializer.metadata_as_dict()


def pls_gather_metadata_file(osf_item, format_key, serializer_config=None) -> SerializedMetadataFile:
    '''for when you want metadata in a file (for saving or downloading)

    @osf_item: the thing (osf model instance or 5-ish character guid string)
    @format_key: str (must be known by osf.metadata.serializers)
    @serializer_config: optional dict (use only when you know the serializer will understand)
    '''
    osfguid = coerce_guid(osf_item, create_if_needed=True)
    basket = pls_get_magic_metadata_basket(osfguid.referent)
    serializer = get_metadata_serializer(format_key, basket, serializer_config)
    return SerializedMetadataFile(
        mediatype=serializer.mediatype,
        filename=serializer.filename_for_itemid(osfguid._id),
        serialized_metadata=serializer.serialize(),
    )


def pls_send_trove_indexcard(osf_item):
    _iri = osf_iri(osf_item)
    if not _iri:
        raise ValueError(f'could not get iri for {osf_item}')
    _metadata_record = pls_gather_metadata_file(osf_item, 'turtle')
    return requests.post(
        _shtrove_ingest_url(),
        params={
            'focus_iri': _iri,
            'record_identifier': _shtrove_record_identifier(osf_item),
        },
        headers={
            'Content-Type': _metadata_record.mediatype,
            **_shtrove_auth_headers(osf_item),
        },
        data=_metadata_record.serialized_metadata,
    )


def pls_delete_trove_indexcard(osf_item):
    return requests.delete(
        _shtrove_ingest_url(),
        params={
            'record_identifier': _shtrove_record_identifier(osf_item),
        },
        headers=_shtrove_auth_headers(osf_item),
    )


def _shtrove_record_identifier(osf_item):
    return osf_item.guids.values_list('_id', flat=True).first()


def _shtrove_ingest_url():
    return f'{website_settings.SHARE_URL}api/v3/ingest'


def _shtrove_auth_headers(osf_item):
    _nonfile_item = (
        osf_item.target
        if hasattr(osf_item, 'target')
        else osf_item
    )
    _access_token = (
        _nonfile_item.provider.access_token
        if _nonfile_item.provider and _nonfile_item.provider.access_token
        else website_settings.SHARE_API_TOKEN
    )
    return {'Authorization': f'Bearer {_access_token}'}
