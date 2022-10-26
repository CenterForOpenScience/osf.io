import rdflib
from rdflib_jsonld.serializer import from_rdf
import rest_framework.serializers as ser

from osf.metadata.gather import gather_guid_graph
from osf.metadata.utils import guid_irl
from api.base.serializers import JSONAPISerializer


# MAX_TYPE_LENGTH = 2**6  # 64
# MAX_KEYWORD_LENGTH = 2**7  # 128
# MAX_TITLE_LENGTH = 2**9  # 512
# MAX_DESCRIPTION_LENGTH = 2**17  # 131072


class GatheredMetadataField(ser.Field):
    def get_attribute(self, metadata_record):
        gathered_graph = gather_guid_graph(metadata_record.guid._id)
        return from_rdf(gathered_graph)

    def to_representation(self, jsonld):
        return jsonld

    def to_internal_value(self, data):
        raise NotImplementedError(f'{self.__class__.__name__} is read-only')


class CustomMetadataSerializer(ser.Serializer):
    def to_internal_value(self, data):
        guid = self.context['guid']
        guid_uri = guid_irl(guid)
        custom_metadata = rdflib.Graph()
        for property_name in self._writable_properties(guid.content_type.model):
            obj = data.get(property_name)
            if obj:
                custom_metadata.set((guid_uri, property_name, obj))
        return from_rdf(custom_metadata)

    def _writable_properties(self, referent_type):
        if referent_type == 'File':
            return [
                'osf:resourceType',
                'osf:resourceTypeGeneral',
                'dct:title',
                'dct:description',
            ]
        if referent_type in ('Node', 'Registration', 'Preprint'):
            return [
                'osf:resourceType',
                'osf:resourceTypeGeneral',
                'osf:funderName',
                'osf:funderIdentifier',
                'osf:funderIdentifierType',
                'osf:awardNumber',
                'osf:awardURI',
                'osf:awardTitle',
            ]
        raise NotImplementedError(f'unknown referent type "{referent_type}"')


class MetadataRecordSerializer(JSONAPISerializer):
    gathered_metadata = GatheredMetadataField(read_only=True)
    custom_metadata = CustomMetadataSerializer()

    def update(self, instance, validated_data):
        instance.custom_metadata_graph = validated_data['as_jsonld']
        instance.save()
        return instance
