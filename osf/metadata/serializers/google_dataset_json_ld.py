import json
from osf.metadata import gather
from osf.metadata.serializers import _base
from osf.metadata.rdfutils import DCT, OSF, FOAF
from website import settings

class GoogleDatasetJsonLdSerializer(_base.MetadataSerializer):
    mediatype = 'application/ld+json'

    def filename(self, osfguid: str):
        return f'{osfguid}-metadata.json-ld'

    def serialize(self, basket: gather.Basket):
        metadata = {
            '@context': 'https://schema.org',
            '@type': 'Dataset',
            'dateCreated': next(basket[DCT.created]),
            'dateModified': next(basket[DCT.modified]),
            'name': next(basket[DCT.title]),
            'description': next(basket[DCT.description], None),
            'url': next(basket[DCT.identifier]),
            'keywords': [keyword for keyword in basket[OSF.keyword]],
            'publisher': {
                '@type': 'Organization',
                'name': 'Center For Open Science'
            },
            'creator': format_creators(basket),
            'identifier': [keyword for keyword in basket[DCT.identifier]],
            'license': next(basket[DCT.rights], None)
        }

        if basket.osf_type == 'Registration':
            _id = basket.focus.guid_metadata_record.guid._id
            registration_metadata = {
                'distribution': [
                    {
                        '@type': 'DataDownload',
                        'contentUrl': f'{settings.WATERBUTLER_URL}/v1/resources/{_id}/providers/osfstorage/?zip=',
                        'encodingFormat': 'URL',
                    },
                ]
            }

            ia_url = next(basket[OSF.archivedAt], None)
            if ia_url:
                registration_metadata['distribution'].append(
                    {
                        '@type': 'DataDownload',
                        'contentUrl': next(basket[OSF.archivedAt]),
                        'encodingFormat': 'URL',
                    }
                )
            metadata.update(registration_metadata)

        return json.dumps(metadata, indent=2, sort_keys=True)


def format_creators(basket):
    creator_data = []
    for creator_iri in basket[DCT.creator]:
        creator_data.append({
            '@type': 'Person',
            'name': next(basket[creator_iri:FOAF.name]),
        })
    return creator_data
