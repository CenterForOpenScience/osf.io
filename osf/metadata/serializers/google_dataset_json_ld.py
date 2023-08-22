import json
from osf.metadata.serializers import _base
from osf.metadata.rdfutils import (
    DCTERMS,
    OSF,
    FOAF,
    OSFIO,
    primitivify_rdf,
)

from website import settings

class GoogleDatasetJsonLdSerializer(_base.MetadataSerializer):
    mediatype = 'application/ld+json'

    def filename_for_itemid(self, itemid: str):
        return f'{itemid}-metadata-schemadotorg.json'

    def serialize(self) -> str:
        return json.dumps(
            self.metadata_as_dict(),
            indent=2,
            sort_keys=True,
        )

    def metadata_as_dict(self) -> dict:
        metadata = {
            '@context': 'https://schema.org',
            '@type': 'Dataset',
            'dateCreated': next(self.basket[DCTERMS.created]),
            'dateModified': next(self.basket[DCTERMS.modified]),
            'name': next(self.basket[DCTERMS.title | OSF.fileName]),
            'description': next(self.basket[DCTERMS.description], None),
            'url': next(url for url in self.basket[DCTERMS.identifier] if url.startswith(OSFIO)),
            'keywords': [keyword for keyword in self.basket[OSF.keyword]],
            'publisher': {
                '@type': 'Organization',
                'name': 'Center For Open Science'
            },
            'creator': format_creators(self.basket),
            'identifier': [identifer for identifer in self.basket[DCTERMS.identifier]],
            'license': format_license_list(self.basket),
        }

        if self.basket.focus.rdftype == OSF.Registration:
            _id = self.basket.focus.guid_metadata_record.guid._id
            registration_metadata = {
                'distribution': [
                    {
                        '@type': 'DataDownload',
                        'contentUrl': f'{settings.WATERBUTLER_URL}/v1/resources/{_id}/providers/osfstorage/?zip=',
                        'encodingFormat': 'URL',
                    },
                ]
            }

            ia_url = next(self.basket[OSF.archivedAt], None)
            if ia_url:
                registration_metadata['distribution'].append(
                    {
                        '@type': 'DataDownload',
                        'contentUrl': ia_url,
                        'encodingFormat': 'URL',
                    }
                )
            metadata.update(registration_metadata)
        return primitivify_rdf(metadata)


def format_creators(basket):
    creator_data = []
    for creator_iri in basket[DCTERMS.creator]:
        creator_data.append({
            '@type': 'Person',
            'name': next(basket[creator_iri:FOAF.name]),
        })
    return creator_data


def format_license_list(basket):
    license_list = []
    for rights_ref in basket[DCTERMS.rights]:
        license_list.append({
            '@type': 'CreativeWork',
            'url': list(basket[rights_ref:DCTERMS.identifier]),
            'name': list(basket[rights_ref:FOAF.name]),
        })
    return license_list
