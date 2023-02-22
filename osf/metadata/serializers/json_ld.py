from osf.metadata import gather
from osf.metadata.serializers import _base
from osf.metadata.rdfutils import DCT, OSF, FOAF


class JsonLdMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'application/ld+json'

    def filename(self, osfguid: str):
        return f'{osfguid}-metadata.json-ld'

    def serialize(self, basket: gather.Basket):
        data = {
            '@context': 'https://schema.org',
            '@type': 'Dataset',
            'dateCreated': next(basket[DCT.created]),
            'dateModified': next(basket[DCT.modified]),
            'name': next(basket[DCT.title]),
            'description': next(basket[DCT.description]),
            'url': next(basket[DCT.identifier]),
            'keywords': [keyword for keyword in basket[OSF.keyword]],
            'publisher': {
                '@type': 'Organization',
                'name': 'Center For Open Science'
            },
            'creator': format_creators(basket),
            'identifier': [keyword for keyword in basket[DCT.identifier]]
        }

        license = next(basket[DCT.rights])
        if license:
            data['license'] = license

        return data


def format_creators(basket):
    creator_data = []
    for creator_iri in basket[DCT.creator]:
        creator_data.append({
            '@type': 'Person',
            'name': next(basket[creator_iri:FOAF.name]),
        })
    return creator_data
