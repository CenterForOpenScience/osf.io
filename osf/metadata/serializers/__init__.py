'''several ways to serialize a basket of metadata into a string.

to add a new serializer, implement a new subclass of
`osf.metadata.serializers._base.MetadataSerializer`
and add it to METADATA_SERIALIZERS with a unique key
'''
from .datacite_json import DataciteJsonMetadataSerializer
from .datacite_xml import DataciteXmlMetadataSerializer
from .turtle import TurtleMetadataSerializer
from .google_dataset_json_ld import GoogleDatasetJsonLdSerializer


METADATA_SERIALIZERS = {
    'turtle': TurtleMetadataSerializer,
    'datacite-json': DataciteJsonMetadataSerializer,
    'datacite-xml': DataciteXmlMetadataSerializer,
    'google-dataset-json-ld': GoogleDatasetJsonLdSerializer,
}
