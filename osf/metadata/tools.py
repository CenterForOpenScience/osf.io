'''for when you don't care about rdf or gatherbaskets, just want metadata about a thing.
'''
import typing

from osf.models.base import coerce_guid
from osf.metadata.osf_gathering import pls_get_magic_metadata_basket
from osf.metadata.serializers import get_metadata_serializer


class SerializedMetadataFile(typing.NamedTuple):
    mediatype: str
    filename: str
    serialized_metadata: str | bytes


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
