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
    """
    User provided fields:

    file_description
    file_description_type
    resource_type
    related_publication_doi
    external_doi_for_file
    funding_agency
    grant_number
    publication_year

    """

    @classmethod
    def serialize_json(cls, record):
        file = record.file
        target = file.target
        doc = {
            'creators': utils.datacite_format_contributors(target.visible_contributors),
            'titles': [
                {
                    # TODO: user can rename in UI, does this change the filename?
                    'title': file.name
                },
                {
                    'title': target.title,
                    'titleType': 'AlternativeTitle'
                }
            ],
            'publisher': 'Open Science Framework',
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

        file_description = record.metadata.get('file_description')
        if file_description:
            doc['descriptions'] = [
                {
                    'description': file_description,
                    'descriptionType': 'Abstract'
                }
            ]
        subjects = target.subjects.values_list('text', flat=True)
        if subjects:
            doc['subjects'] = utils.datacite_format_subjects(subjects)

        resource_type = record.metadata.get('resource_type', '(:unas)')
        doc['resourceType'] = {
            'resourceType': resource_type,
            'resourceTypeGeneral': utils.RESOURCE_TYPE_MAP.get(resource_type)
        }

        # TODO: keep publicationYear manually overridable by the user?
        doc['publicationYear'] = record.metadata.get('publication_year', str(file.created.year))

        # TODO - save this as the identifier?
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
        if funder_name:
            funding_info = {
                'funderName': funder_name
            }
            if award_number:
                funding_info['awardNumber'] = award_number
            doc['fundingReferences'] = [funding_info]

        if getattr(target, 'node_license', None):
            doc['rightsList'] = [utils.datacite_format_rights(target.node_license)]

        doc['version'] = file.versions.all().order_by('-created').first().identifier

        return doc

    @classmethod
    def serialize_xml(cls, record):
        data = cls.serialize_json(record)
        return schema40.tostring(data)

    @classmethod
    def validate(cls, record, json_data):
        # The OSF cannot currently issue DOIs for a file, which is required for validation.
        # Manually add a placeholder if one is not provided by the user.
        if not json_data.get('external_doi_for_file', None):
            placeholder = DOI_FORMAT.format(prefix=DATACITE_PREFIX, guid='placeholder')
            json_data['identifier'] = {'identifierType': 'DOI', 'identifier': placeholder}
        return super(DataciteMetadataRecordSerializer, cls).validate(record, json_data)

    @classmethod
    def update(cls, record, json_data):
        """ Update the json given from the user, using the user-facing datacite schema

        :param FileMetadataRecord record: file metadata record to be updated
        :param dict json_data: data entered by the user, in dict format
        """
        # TODO: add validation for user provided fields
        record.metadata = json_data
        record.save()
