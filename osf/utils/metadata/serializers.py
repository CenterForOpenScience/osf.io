from website.settings import DOMAIN, DOI_FORMAT, DATACITE_PREFIX
from datacite import schema40
import jsonschema

serializer_registry = {}

def register(schema_name):
    """Register classes into serializer_registry"""
    def decorator(cls):
        serializer_registry[schema_name] = cls
        return cls
    return decorator


class SchemaSerializer(object):

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


@register(schema_name='datacite')
class DataciteMetadataSerializer(SchemaSerializer):

    @classmethod
    def serialize_json(cls, record):
        file = record.file
        target = file.target
        creators = []
        for contrib in target.visible_contributors:
            creator = {
                'creatorName': contrib.fullname,
                'givenName': contrib.given_name,
                'familyName': contrib.family_name,
                'nameIdentifiers': [{
                    'nameIdentifier': contrib._id,
                    'nameIdentifierScheme': 'OSF',
                    'schemeURI': DOMAIN
                }]
            }

            if contrib.external_identity:
                for key, value in contrib.external_identity.items():
                    creator['nameIdentifiers'].append({
                        'nameIdentifier': value.keys()[0],  # This is only good for ORCID and likely to break unless more validation is put in.
                        'nameIdentifierScheme': key
                    })

            creators.append(creator)

        doc = {
            'identifier': {
                'identifier': DOI_FORMAT.format(prefix=DATACITE_PREFIX, guid=target._id),
                'identifierType': 'DOI'
            },
            'creators': creators,
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

        #subjects = target.subjects.values_list('text', flat=True)
        #if subjects:
        #    doc['subjects'] = datacite_format_subjects_json(subjects)

        resource_type = record.metadata.get('resource_type')
        resource_type_general = record.metadata.get('resource_type_general')
        if resource_type:
            doc['resourceType'] = {
                'resourceType': resource_type,
                'resourceTypeGeneral': resource_type_general
            }
        else:
            doc['resourceType'] = {
                'resourceType': '(unas)',
                'resourceTypeGeneral': 'Other'
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

        return doc

    @classmethod
    def serialize_xml(cls, record):
        data = cls.serialize_json(record)
        return schema40.tostring(data)
