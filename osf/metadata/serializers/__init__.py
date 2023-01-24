from .datacite_json import DataciteJsonMetadataSerializer
from .datacite_xml import DataciteXmlMetadataSerializer
from .turtle import TurtleMetadataSerializer


METADATA_SERIALIZERS = {
    'turtle': TurtleMetadataSerializer,
    'datacite-json': DataciteJsonMetadataSerializer,
    'datacite-xml': DataciteXmlMetadataSerializer,
}
