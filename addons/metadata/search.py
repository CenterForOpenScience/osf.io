import json
import logging
import os

from django.core.paginator import Paginator
from website.search.util import (
    unicode_normalize,
)
from . import SHORT_NAME

logger = logging.getLogger(__name__)


def _extract_metadata_text(file_metadata):
    metadata_props = file_metadata.metadata_properties
    if 'items' not in metadata_props:
        return ''
    text = []
    for item in metadata_props['items']:
        if 'data' not in item:
            continue
        for value in item['data'].values():
            if 'value' not in value:
                continue
            if value['value'] is None:
                continue
            if isinstance(value['value'], list) or isinstance(value['value'], dict):
                text.append(json.dumps(value['value']))
                continue
            text.append(value['value'])
    return ' '.join(text)

def serialize_file_metadata(file_metadata, category):
    node = file_metadata.project.owner
    elastic_document = {}
    path = file_metadata.path
    normalized_path = unicode_normalize(path)

    creator = file_metadata.creator
    if creator:
        creator_id = creator._id
        creator_name = unicode_normalize(creator.fullname)
    else:
        creator_id = ''
        creator_name = ''

    modifier = file_metadata.user
    if modifier:
        modifier_id = modifier._id
        modifier_name = unicode_normalize(modifier.fullname)
    else:
        modifier_id = ''
        modifier_name = ''
    _, file_name = os.path.split(path.rstrip('/'))

    elastic_document = {
        'id': file_metadata._id,
        'path': normalized_path,
        'sort_file_name': file_name,
        'sort_node_name': node.title,
        'category': category,
        'node_public': node.is_public,
        'date_created': file_metadata.created,
        'date_modified': file_metadata.modified,
        'creator_id': creator_id,
        'creator_name': creator_name,
        'modifier_id': modifier_id,
        'modifier_name': modifier_name,
        'node_title': node.title,
        'normalized_node_title': unicode_normalize(node.title),
        'node_url': node.url,
        # Contributors for Access control
        'node_contributors': [
            {
                'id': x['guids___id']
            }
            for x in node._contributors.all().order_by('contributor___order')
            .values('guids___id')
        ],
        'url': file_metadata.resolve_urlpath(),
        'text': unicode_normalize(_extract_metadata_text(file_metadata)),
    }
    return elastic_document

def migrate_file_metadata(search, index, delete):
    from .models import FileMetadata
    logger.info('Migrating file_metadata to index: {}'.format(index))
    file_metadata = FileMetadata.objects.order_by('-id')
    increment = 100
    paginator = Paginator(file_metadata, increment)
    for page_number in paginator.page_range:
        logger.info('Updating page {} / {}'.format(page_number, paginator.num_pages))
        search.bulk_update_file_metadata(paginator.page(page_number).object_list, index=index)
    logger.info('{} file_metadata migrated'.format(file_metadata.count()))

def build_private_search_match_query(user):
    return {
        'bool': {
            'must': [
                {
                    'term': {
                        'category': SHORT_NAME,
                    }
                },
                {
                    'bool': {
                        'should': [
                            {
                                'term': {
                                    'node_contributors.id': user._id
                                }
                            },
                            {
                                'term': {
                                    'node_public': True
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }
