from osf.metadata import gather
from osf.metadata.serializers import _base


class JsonLdMetadataSerializer(_base.MetadataSerializer):
    mediatype = 'text/json-ld'

    def filename(self, osfguid: str):
        return f'{osfguid}-metadata.json-ld'

    def serialize(self, basket: gather.Basket):
        node = basket.focus.dbmodel

        data = {
            '@context': 'https://schema.org',
            '@type': 'Dataset',
            'dateCreated': str(node.created),
            'dateModified': str(node.modified),
            'name': node.title,
            'description': node.description,
            'url': node.absolute_url,
            'keywords': [tag.name for tag in node.tags.all()],
            'publisher': {
                '@type': 'Organization',
                'name': 'Center For Open Science'
            },
            'creator': format_creators(node),
            'distribution': format_distribution(node),
        }

        if node.license:
            data['license'] = node.license.url

        if node.identifiers.exists():
            data['identifier'] = f'https://doi.org/{node.identifiers.get(category="doi").value}'

        return data


def format_creators(node):
    creator_json = []
    for contributor in node.contributors.all():
        creator_json.append({
            '@type': 'Person',
            'name': contributor.fullname,
        })

    return creator_json


def format_distribution(node):
    return [
        {
            '@type': 'DataDownload',
            'contentUrl': f'{node.osfstorage_region.waterbutler_url}/v1/resources/{node._id}/providers/osfstorage/?zip=',
            'encodingFormat': 'URL',
        }
    ]


def format_identifier(node):
    return [
        {
            'contentUrl': f'{node.osfstorage_region.waterbutler_url}/v1/resources/{node._id}/providers/osfstorage/?zip=',
        }
    ]
