"""several ways to serialize a basket of metadata into a string.

to add a new serializer, implement a new subclass of
`osf.metadata.serializers._base.MetadataSerializer`
and add it to METADATA_SERIALIZER_REGISTRY with a unique key
"""

from osf import exceptions
from osf.metadata import gather
from .datacite import (
    DataciteJsonMetadataSerializer,
    DataciteXmlMetadataSerializer,
)
from .google_dataset_json_ld import GoogleDatasetJsonLdSerializer
from .turtle import TurtleMetadataSerializer


METADATA_SERIALIZER_REGISTRY = {
    "turtle": TurtleMetadataSerializer,
    "datacite-json": DataciteJsonMetadataSerializer,
    "datacite-xml": DataciteXmlMetadataSerializer,
    "google-dataset-json-ld": GoogleDatasetJsonLdSerializer,
}


def get_metadata_serializer(
    format_key: str, basket: gather.Basket, serializer_config=None
):
    try:
        serializer_class = METADATA_SERIALIZER_REGISTRY[format_key]
    except KeyError:
        valid_formats = ", ".join(METADATA_SERIALIZER_REGISTRY.keys())
        raise exceptions.InvalidMetadataFormat(format_key, valid_formats)
    else:
        return serializer_class(basket, serializer_config)
