import rdflib
from rdflib_jsonld.serializer import from_rdf
import rest_framework.serializers as ser

from osf.metadata.gather import gather_guid_graph
from osf.metadata import rdfutils
from osf.models.metadata import GuidMetadataRecord
from api.base.serializers import JSONAPISerializer
from api.base.utils import absolute_reverse


# MAX_TYPE_LENGTH = 2**6  # 64
# MAX_KEYWORD_LENGTH = 2**7  # 128
# MAX_TITLE_LENGTH = 2**9  # 512
# MAX_DESCRIPTION_LENGTH = 2**17  # 131072


class GatheredMetadataField(ser.Field):
    def get_attribute(self, guid):
        gathered_graph = gather_guid_graph(guid._id)
        return from_rdf(gathered_graph, auto_compact=True)

    def to_representation(self, jsonld):
        return jsonld

    def to_internal_value(self, data):
        raise NotImplementedError(f'{self.__class__.__name__} is read-only')


class CustomMetadataField(ser.Field):
    def get_attribute(self, guid):
        return GuidMetadataRecord.objects.for_guid(guid).custom_metadata_graph

    def to_representation(self, custom_metadata_graph):
        return custom_metadata_graph.serialize(format='json-ld')

    def to_internal_value(self, data):
        guid = self.context['guid']
        guid_uri = rdfutils.guid_irl(guid)
        custom_metadata = rdflib.Graph()
        for property_name in self._writable_properties(guid.content_type.model):
            obj = data.get(property_name)
            if obj:
                custom_metadata.set((guid_uri, property_name, obj))
        return from_rdf(custom_metadata, auto_compact=True)

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


class TwoFieldMetadataRecordSerializer(JSONAPISerializer):
    gathered_metadata = GatheredMetadataField(read_only=True)
    custom_metadata = CustomMetadataField()

    class Meta:
        type_ = 'metadata-records'

    def update(self, guid, validated_data):
        metadata_record = GuidMetadataRecord.objects.for_guid(guid)
        metadata_record.custom_metadata_graph = validated_data['as_jsonld']
        metadata_record.save()
        return guid


class MetadataRecordJSONAPISerializer(ser.BaseSerializer):
    def to_representation(self, guid):
        gathered_graph = gather_guid_graph(guid._id)
        return self._build_jsonapi_resource(guid, gathered_graph)

    def to_internal_value(self, data):
        pass

    def update(self, guid, validated_data):
        pass

    def _build_jsonapi_resource(self, guid, graph):
        focus = rdfutils.guid_irl(guid)
        attributes = {}
        relationships = {}
        for (subj, pred, obj) in graph.triples((focus, None, None)):
            # TODO: use osf-map owl to infer attribute vs relation, one vs many
            if isinstance(obj, rdflib.Literal):
                attributes.setdefault(pred, []).append(obj)
            elif isinstance(obj, rdflib.URIRef):
                relationships.setdefault(pred, []).append(obj)
            elif isinstance(obj, rdflib.BNode):
                pass  # TODO
        return {
            '@context': rdfutils.JSONAPI_CONTEXT,
            'id': f'osfio:{guid._id}',
            'type': 'metadata-records',
            'attributes': attributes,
            'relationships': relationships,
            'links': {
                'self': absolute_reverse(
                    'metadata-records:metadata-record-detail',
                    kwargs={'guid_id': guid._id},
                ),
            },
        }
