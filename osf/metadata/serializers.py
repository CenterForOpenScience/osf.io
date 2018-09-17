import jsonschema
from datacite import schema40

from osf.metadata import utils
from website.settings import DOMAIN

serializer_registry = {}

def register(schema_id):
    """Register classes into serializer_registry"""
    def decorator(cls):
        serializer_registry[schema_id] = cls
        return cls
    return decorator


class MetadataRecordSerializer(object):

    def serialize_json(self, metadata_record):
        raise NotImplementedError

    def serialize_xml(self, metadata_record):
        raise NotImplementedError

    @classmethod
    def serialize(cls, metadata_record, format='json'):
        if format == 'json':
            return cls.serialize_json(metadata_record)
        elif format == 'xml':
            return cls.serialize_xml(metadata_record)

    @classmethod
    def validate(cls, record, json_data):
        return jsonschema.validate(json_data, record.schema.schema)

    @classmethod
    def update(cls, record, json_data):
        if cls.validate(json_data):
            record.metadata.update(json_data)


@register(schema_id='datacite')
class DataciteMetadataRecordSerializer(MetadataRecordSerializer):

    @classmethod
    def serialize_json(cls, record):
        file = record.file
        target = file.target
        doc = {
            'identifier': utils.datacite_format_identifier(target),
            'creators': utils.datacite_format_contributors(target.visible_contributors),
            'titles': [
                {
                    'title': file.name
                },
                {
                    'title': target.title,
                    'titleType': 'AlternativeTitle'
                }
            ],
            'publisher': 'Open Science Framework',
            'publicationYear': str(file.created.year),
            'dates': [
                {
                    'date': str(file.created),
                    'dateType': 'Created'
                },
                {
                    'date': str(file.modified),
                    'dateType': 'Updated'
                }
            ],
        }

        if target.description:
            doc['descriptions'] = [
                {
                    'description': target.description,
                    'descriptionType': 'Abstract'
                }
            ]

        subjects = target.subjects.values_list('text', flat=True)
        if subjects:
           doc['subjects'] = utils.datacite_format_subjects(subjects)

        resource_type = record.metadata.get('resource_type', '(unas)')
        resource_type_general = record.metadata.get('resource_type_general', utils.RESOURCE_TYPE_MAP.get(resource_type))
        doc['resourceType'] = {
            'resourceType': resource_type,
            'resourceTypeGeneral': resource_type_general
        }

        related_publication_doi = record.metadata.get('related_publication_doi')
        if related_publication_doi:
            doc['relatedIdentifiers'] = [
                {
                    'relatedIdentifier': related_publication_doi,
                    'relatedIdentifierType': 'DOI'
                }
            ]

        file_guid = file.get_guid()
        if file_guid:
            doc['alternateIdentifiers'] = [
                {
                    'alternateIdentifier': DOMAIN + file_guid,
                    'alternateIdentifierType': 'URL'
                }
            ]

        funder_name = record.metadata.get('funding_agency')
        award_number = record.metadata.get('grant_number')
        if funder_name or award_number:
            doc['fundingReferences'] = []
            if funder_name:
                doc['fundingReferences'].append({
                    'funderName': funder_name
                })
            if award_number:
                doc['fundingReferences'].append({
                    'awardNumber': award_number
                })

        if getattr(target, 'node_license', None):
            doc['rightsList'] = [utils.datacite_format_rights(target.node_license)]

        return doc

    @classmethod
    def serialize_xml(cls, record):
        data = cls.serialize_json(record)
        return schema40.tostring(data)
