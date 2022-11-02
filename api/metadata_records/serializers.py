import rdflib
import rest_framework.serializers as ser

from osf.metadata.gather import gather_guid_metadata
from osf.metadata import rdfutils
from api.base.utils import absolute_reverse


# MAX_TYPE_LENGTH = 2**6  # 64
# MAX_KEYWORD_LENGTH = 2**7  # 128
# MAX_TITLE_LENGTH = 2**9  # 512
# MAX_DESCRIPTION_LENGTH = 2**17  # 131072


# class CustomMetadataField(ser.Field):
#     def get_attribute(self, guid):
#         return GuidMetadataRecord.objects.for_guid(guid).custom_metadata_graph
#
#     def to_representation(self, custom_metadata_graph):
#         return custom_metadata_graph.serialize(format='json-ld')
#
#     def to_internal_value(self, data):
#         guid = self.context['guid']
#         guid_uri = rdfutils.guid_irl(guid)
#         custom_metadata = rdflib.Graph()
#         for property_name in self._writable_properties(guid.content_type.model):
#             obj = data.get(property_name)
#             if obj:
#                 custom_metadata.set((guid_uri, property_name, obj))
#         return from_rdf(custom_metadata, auto_compact=True)
#
#     def _writable_properties(self, referent_type):
#         if referent_type == 'File':
#             return [
#                 'osf:resourceType',
#                 'osf:resourceTypeGeneral',
#                 'dct:title',
#                 'dct:description',
#             ]
#         if referent_type in ('Node', 'Registration', 'Preprint'):
#             return [
#                 'osf:resourceType',
#                 'osf:resourceTypeGeneral',
#                 'osf:funderName',
#                 'osf:funderIdentifier',
#                 'osf:funderIdentifierType',
#                 'osf:awardNumber',
#                 'osf:awardURI',
#                 'osf:awardTitle',
#             ]
#         raise NotImplementedError(f'unknown referent type "{referent_type}"')


class MetadataRecordJSONAPISerializer(ser.BaseSerializer):
    def to_representation(self, guid):
        gathered_graph = gather_guid_metadata(guid)
        resource_builder = RdfToJsonapiResource(
            rdf_graph=gathered_graph,
            focus_iri=rdfutils.guid_irl(guid),
            include_paths=self._include_paths(),
        )
        return {
            '@context': rdfutils.OSFJSONAPI_CONTEXT,
            'data': resource_builder.jsonapi_representation(),
            'included': list(self._get_included(resource_builder.to_include)),
        }

    def to_internal_value(self, data):
        pass

    def update(self, guid, validated_data):
        pass

    def _include_paths(self):
        # TODO: `include` query param, helpful defaults by focus rdf:type
        # TODO: handle multi-step paths, e.g. ?include=dct:isPartOf.dct:creator
        return [
            rdflib.DCTERMS.creator,
            rdflib.DCTERMS.contributor,
        ]

    def _get_included(self, to_include):
        for resource_iri in to_include:
            included_graph = gather_guid_metadata(resource_iri)
            builder = RdfToJsonapiResource(
                rdf_graph=included_graph,
                focus_iri=resource_iri,
                # TODO: include_paths=
            )
            yield builder.jsonapi_representation()
            # TODO: deeper includes
            # yield from self._get_included(builder.to_include)


class RdfToJsonapiResource:
    def __init__(self, rdf_graph, focus_iri, include_paths=()):
        self.rdf_graph = rdf_graph
        self.focus_iri = focus_iri
        self.include_paths = include_paths
        self.attributes = {}
        self.relationships = {}
        self.to_include = set()
        self._build()

    def jsonapi_representation(self):
        return {
            'id': self._compact_iri(self.focus_iri),
            'type': 'metadata-records',
            '@type': self._compact_iri(self.rdf_graph.value(self.focus_iri, rdflib.RDF.type)),
            'attributes': self.attributes,
            'relationships': self.relationships,
            'links': {
                'self': self._metadata_record_api_url(self.focus_iri),
            },
        }

    def _build(self):
        for predicate in set(self.rdf_graph.predicates(subject=self.focus_iri)):
            # TODO: use osf-map owl to infer attribute vs relation, one vs many
            if self._is_attribute(predicate):
                self._add_attribute(predicate)
            elif self._is_relationship(predicate):
                self._add_relationship(predicate)
            elif predicate not in (rdflib.RDF.type, rdflib.DCTERMS.identifier):
                print(f'!! skipping predicate {predicate}')

    def _add_attribute(self, predicate):
        values = [
            self._format_attr_value(value)
            for value in self.rdf_graph.objects(
                subject=self.focus_iri,
                predicate=predicate,
            )
        ]
        # TODO: use owl/osf-map for property vs list
        if len(values) == 1:
            attribute_value = values[0]
        else:
            attribute_value = values
        self.attributes[self._compact_iri(predicate)] = attribute_value

    def _add_relationship(self, predicate):
        object_ids = list(self.rdf_graph.objects(subject=self.focus_iri, predicate=predicate))
        if self._should_include(predicate):
            self.to_include.update(filter(None, object_ids))

        formatted_objects = [self._format_related_ref(obj) for obj in object_ids]
        # TODO: use owl/osf-map for to-one vs to-many
        if len(formatted_objects) == 1:
            formatted_relationship = {'data': formatted_objects[0]}
        else:
            formatted_relationship = {'data': formatted_objects}
        self.relationships[self._compact_iri(predicate)] = formatted_relationship

    def _format_attr_value(self, value):
        if isinstance(value, rdflib.URIRef):
            return self._compact_iri(value)
        return value

    def _format_related_ref(self, related_iri):
        related_type = self.rdf_graph.value(related_iri, rdflib.RDF.type)
        return {
            'id': self._compact_iri(related_iri),
            'type': 'metadata-records',
            '@type': self._compact_iri(related_type),
        }

    def _format_nested(self, rdf_graph, triple):
        pass  # TODO

    def _is_attribute(self, predicate):
        # TODO: use owl/osf-map
        return predicate in (
            rdflib.DCTERMS.available,
            rdflib.DCTERMS.description,
            rdflib.DCTERMS.title,
            rdflib.DCTERMS.rightsHolder,
            rdflib.DCTERMS.dateCopyrighted,
            rdflib.DCTERMS.modified,
            rdflib.DCTERMS.created,
            rdflib.DCTERMS.type,
            rdfutils.OSF.keyword,
            rdfutils.OSF.file_name,
            rdfutils.OSF.file_path,
        )

    def _is_relationship(self, predicate):
        # TODO: use owl/osf-map
        return predicate in (
            rdflib.DCTERMS.isPartOf,
            rdflib.DCTERMS.hasPart,
            rdflib.DCTERMS.creator,
        )

    def _compact_iri(self, iri):
        # for a guid irl, returns 'osfio:<guid>'
        return self.rdf_graph.qname(iri)

    def _metadata_record_api_url(self, guid_ref):
        guid_id = rdfutils.try_guid_from_irl(guid_ref)
        if guid_id is not None:
            return absolute_reverse(
                'metadata-records:metadata-record-detail',
                kwargs={'guid_id': guid_id},
            )
        return None

    def _should_include(self, predicate):
        # TODO: handle multi-step paths
        return (predicate in self.include_paths)
