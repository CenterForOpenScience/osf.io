import json
import jsonschema
from datacite import schema40

from osf.metadata import utils
from website.settings import DOMAIN, DOI_FORMAT, DATACITE_PREFIX

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
        if format == 'xml':
            return cls.serialize_xml(metadata_record)
        raise ValueError('Format "{}" is not supported.'.format(format))

    @classmethod
    def validate(cls, record):
        # note: this is not used at the moment, because it is overridden by the datacite subclass.
        # Future subclasses should not need to override validate.
        return jsonschema.validate(cls.serialize(record), record.schema.schema)


@register(schema_id='datacite')
class DataciteMetadataRecordSerializer(MetadataRecordSerializer):

    osf_schema = 'user_entered_datacite.json'

    @classmethod
    def serialize_json(cls, record):
        osfstorage_file = record.file
        target = osfstorage_file.target
        target.reload()
        doc = {
            'creators': utils.datacite_format_contributors(target.visible_contributors),
            'titles': [
                {
                    'title': osfstorage_file.name
                },
                {
                    'title': target.title,
                    'titleType': 'AlternativeTitle'
                }
            ],
            'publisher': 'Open Science Framework',
            'dates': [
                {
                    'date': str(osfstorage_file.created),
                    'dateType': 'Created'
                },
                {
                    'date': str(osfstorage_file.modified),
                    'dateType': 'Updated'
                }
            ],
        }

        file_description = record.metadata.get('file_description')
        if file_description:
            doc['descriptions'] = [
                {
                    'description': file_description,
                    'descriptionType': 'Abstract'
                }
            ]

        subject_list = []
        subjects_from_target = target.subjects.all().select_related('bepress_subject')
        if subjects_from_target.exists():
            subject_list = utils.datacite_format_subjects(subjects_from_target)
        tags_on_file = osfstorage_file.tags.values_list('name', flat=True)
        for tag_name in tags_on_file:
            subject_list.append({'subject': tag_name})
        if subject_list:
            doc['subjects'] = subject_list

        resource_type = record.metadata.get('resource_type', '(:unas)')
        doc['resourceType'] = {
            'resourceType': resource_type,
            'resourceTypeGeneral': utils.RESOURCE_TYPE_MAP.get(resource_type)
        }

        doc['publicationYear'] = str(osfstorage_file.created.year)

        related_publication_doi = record.metadata.get('related_publication_doi')
        if related_publication_doi:
            doc['relatedIdentifiers'] = [
                {
                    'relatedIdentifier': related_publication_doi,
                    'relatedIdentifierType': 'DOI',
                    'relationType': 'IsSupplementTo'
                }
            ]

        if osfstorage_file.guids.exists():
            doc['alternateIdentifiers'] = [
                {
                    'alternateIdentifier': DOMAIN + osfstorage_file.guids.first()._id,
                    'alternateIdentifierType': 'URL'
                }
            ]

        funder_name = record.metadata.get('funding_agency')
        award_number = record.metadata.get('grant_number')
        if funder_name:
            funding_info = {
                'funderName': funder_name
            }
            if award_number:
                funding_info['awardNumber'] = award_number
            doc['fundingReferences'] = [funding_info]

        if getattr(target, 'node_license', None):
            doc['rightsList'] = [utils.datacite_format_rights(target.node_license)]

        latest_version_identifier = osfstorage_file.versions.all().order_by('-created').values_list('identifier', flat=True)
        if latest_version_identifier:
            doc['version'] = latest_version_identifier[0]

        return json.dumps(doc)

    @classmethod
    def serialize_xml(cls, record):
        data = json.loads(cls.serialize_json(record))
        return schema40.tostring(data)

    @classmethod
    def validate(cls, record):
        # This method needs to be overridden because the OSF cannot currently
        # issue DOIs for a file, which is required for datacite schema validation.
        # Manually add a placeholder for validation until we handle this better.
        json_data = json.loads(cls.serialize_json(record))
        placeholder = DOI_FORMAT.format(prefix=DATACITE_PREFIX, guid='placeholder')
        json_data['identifier'] = {'identifierType': 'DOI', 'identifier': placeholder}
        return jsonschema.validate(json_data, record.schema.schema)
