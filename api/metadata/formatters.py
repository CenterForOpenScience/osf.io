from website import settings
from website.identifiers.metadata import (
    datacite_format_creators_json,
    datacite_format_subjects_json,
)

class FileMetadataFormatter(object):

    @property
    def metaschema_id(self):
        raise NotImplementedError('FileMetadataFormatter subclasses must define metaschema_id.')

    def validate(self, metadata):
        raise NotImplementedError('FileMetadataFormatter subclasses must implement a validate method.')

    def format_json(self, file_node, metadata):
        raise NotImplementedError('JSON formatter for {} not implemented.'.format(self))

    def format_xml(self, file_node, metadata):
        raise NotImplementedError('XML formatter for {} not implemented.'.format(self))

    def format(self, file_node, metadata, type='json'):
        if type == 'json':
            return self.format_json(file_node, metadata)


class DataCiteMetadataFormatter(FileMetadataFormatter):

    metaschema_id = 'datacite'

    RESOURCE_TYPE_MAP = {
        'Audio/Video': 'Audiovisual',
        'Dataset': 'Dataset',
        'Image': 'Image',
        'Model': 'Model',
        'Software': 'Software',
        'Book': 'Text',
        'Funding Submission': 'Text',
        'Journal Article': 'Text',
        'Lesson': 'Text',
        'Poster': 'Text',
        'Preprint': 'Text',
        'Presentation': 'Text',
        'Research Tool': 'Text',
        'Thesis': 'Text',
        'Other': 'Text'
    }

    def validate(self, metadata):
        pass

    def format_xml(self, metadata):
        pass

    def format_json(self, metadata_record):
        doc = {
            'identifier': {
                'identifier': ':tba'
            },
            'creators': datacite_format_creators_json(metadata_record.file.node.visible_contributors),
            'titles': [
                {
                    'title': metadata_record.file.name
                },
                {
                    'title': metadata_record.file.node.title,
                    'titleType': 'AlternativeTitle'
                }
            ],
            'publisher': 'OSF',
            'publicationYear': metadata_record.file.created.year,
            'dates': [
                {
                    'date': metadata_record.file.created,
                    'dateType': 'available'
                },
                {
                    'date': metadata_record.file.modified,
                    'dateType': 'updated'
                }
            ],


        }

        description = metadata_record.metadata.get('description')
        if description:
            doc['description'] = [
                {
                    'description': description,
                    'descriptionType': 'Abstract'
                }
            ]

        subjects = metadata_record.file.node.subjects.values_list('text', flat=True)
        if subjects:
            doc['subjects'] = datacite_format_subjects_json(subjects)

        resource_type = metadata_record.metadata.get('resource_type')
        if resource_type:
            doc['resourceType'] = [
                {
                    'resourceType': resource_type,
                    'resourceTypeGeneral': self.RESOURCE_TYPE_MAP[resource_type]
                }
            ]
        else:
            doc['resourceType'] = ':unas'

        related_publication_doi = metadata_record.metadata.get('related_publication_doi')
        if related_publication_doi:
            doc['relatedIdentifiers'] = [
                {
                    'relatedIdentifier': related_publication_doi,
                    'relatedIdentifierType': 'DOI'
                }
            ]

        file_guid = metadata_record.file.get_guid()
        if file_guid:
            doc['alternateIdentifiers'] = [
                {
                    'alternateIdentifier': settings.DOMAIN + file_guid,
                    'alternateIdentifierType': 'URL'
                }
            ]

        funder_name = metadata_record.metadata.get('funding_agency')
        award_number = metadata_record.metadata.get('grant_number')
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
