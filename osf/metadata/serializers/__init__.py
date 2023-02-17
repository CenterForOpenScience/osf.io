'''several ways to serialize a basket of metadata into a string.

to add a new serializer, implement a new subclass of
`osf.metadata.serializers._base.MetadataSerializer`
and add it to METADATA_SERIALIZERS with a unique key
'''
from .datacite_json import DataciteJsonMetadataSerializer
from .datacite_xml import DataciteXmlMetadataSerializer
from .turtle import TurtleMetadataSerializer
from .json_ld import JsonLdMetadataSerializer


METADATA_SERIALIZERS = {
    'turtle': TurtleMetadataSerializer,
    'datacite-json': DataciteJsonMetadataSerializer,
    'datacite-xml': DataciteXmlMetadataSerializer,
    'json-ld': JsonLdMetadataSerializer,
}
