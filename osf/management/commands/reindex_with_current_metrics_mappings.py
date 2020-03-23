"""
Reindex data to use current mapping for ES metrics classes
"""
import logging

from django.core.management.base import BaseCommand
from elasticsearch_dsl import connections
from elasticsearch_metrics.registry import registry

logger = logging.getLogger(__name__)


def get_metric_class(index_name: str) -> type:
    app_label, model_name = index_name.split('_')[:2]
    return registry.all_metrics[app_label][model_name]


def increment_index_versions(client, old_indices: list):
    """
    Increment versions numbers for new indices, these kind don't matter because they should always be aliased to
    the original format of {app_label}_{cls.__name__.lower()}_{year}.

    :param old_indices: indices to be updated
    :return: indices names that are going to be reindexed into.
    """
    new_indices = []
    for index in old_indices:
        index_name = list(client.indices.get(index).keys())[0]  # in case we've already aliased this index
        if '_v' in index_name and index_name[-1].isdigit():
            name, version_num = index_name.split('_v')
            new_index = f'{name}_v{int(version_num) + 1}'
        else:
            new_index = f'{index}_v2'
        new_indices.append(new_index)

    return new_indices


def reindex_and_alias(old_indices: list):
    """
    To migrate data in ES with new mappings is a 4 step process:
    1) Create an index with new mappings
    2) Reindex data from old to new
    3) Delete the old index
    4) Alias the new index so it references the old.

    :param old_indices: indices with data that has old mappings
    :return: None
    """
    client = connections.get_connection()
    new_indices = increment_index_versions(client, old_indices)

    for old_index, new_index in zip(old_indices, new_indices):
        metric_class = get_metric_class(old_index)
        client.indices.create(new_index, body=metric_class._index.to_dict(), params={'wait_for_active_shards': 1})
        body = {
            'source': {
                'index': old_index
            },
            'dest': {
                'index': new_index
            }
        }
        client.reindex(body, params={'wait_for_completion': 'true'})
        old_index_name = list(client.indices.get(old_index).keys())[0]  # in case we've already aliased this index
        client.indices.delete(old_index_name)
        client.indices.put_alias(new_index, old_index)


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--indices',
            type=str,
            nargs='+',
            help='List of indices to be reindexed and remapped'
        )

    def handle(self, *args, **options):
        indices = options.get('indices', [])
        reindex_and_alias(indices)
