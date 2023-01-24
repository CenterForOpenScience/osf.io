import typing

from osf import exceptions
from .serializers import METADATA_SERIALIZERS
from .gather.osf import coerce_guid, pls_gather_item_metadata


class SerializedGuidMetadataFile(typing.NamedTuple):
    mediatype: str
    filename: str
    serialized_metadata: str


def pls_gather_metadata_file(osf_item, format_key, serializer_config=None) -> SerializedGuidMetadataFile:
    try:
        serializer_class = METADATA_SERIALIZERS[format_key]
    except KeyError:
        valid_formats = ', '.join(METADATA_SERIALIZERS.keys())
        raise exceptions.InvalidMetadataFormat(format_key, valid_formats)
    else:
        osfguid = coerce_guid(osf_item, create_if_needed=True)
        basket = pls_gather_item_metadata(osfguid.referent)
        serializer = serializer_class(serializer_config)
        return SerializedGuidMetadataFile(
            mediatype=serializer.mediatype,
            filename=serializer.filename(osfguid._id),
            serialized_metadata=serializer.serialize(basket),
        )
