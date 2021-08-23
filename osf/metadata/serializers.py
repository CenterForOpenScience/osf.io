import json
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
        if format == 'xml':
            return cls.serialize_xml(metadata_record)
        raise ValueError('Format "{}" is not supported.'.format(format))


@register(schema_id='datacite')
class DataciteMetadataRecordSerializer(MetadataRecordSerializer):

    osf_schema = 'osf_datacite.json'

    @classmethod
    def serialize_json(cls, record):
        osfstorage_file = record.file
        target = osfstorage_file.target
        doc = {
            'creators': utils.datacite_format_creators(target.visible_contributors),
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
        if target.subjects.all().exists():
            subject_list = utils.datacite_format_subjects(target)
        tags_on_file = osfstorage_file.tags.values_list('name', flat=True)
        for tag_name in tags_on_file:
            subject_list.append({'subject': tag_name})
        if subject_list:
            doc['subjects'] = subject_list

        resource_type = record.metadata.get('resource_type', '(:unas)')
        doc['resourceType'] = {
            'resourceType': resource_type,
            'resourceTypeGeneral': utils.DATACITE_RESOURCE_TYPE_MAP.get(resource_type)
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

        funders = record.metadata.get('funders')
        if funders:
            doc['fundingReferences'] = []
            for funder in funders:
                funder_info = {}
                if funder.get('funding_agency'):
                    funder_info['funderName'] = funder['funding_agency']
                if funder.get('grant_number'):
                    funder_info['awardNumber'] = {'awardNumber': funder['grant_number']}

                doc['fundingReferences'].append(funder_info)

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
