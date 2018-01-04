""" Script for removing nodes with 'qatest' tags from elastic search index """
import logging
import sys

import django
django.setup()

from website.app import init_app
from django.db.models import Q
from osf.models import AbstractNode
from website.project.tasks import update_node_share
from website.search.elastic_search import update_node
from api.base.settings import DO_NOT_INDEX_LIST
from framework.database import paginated


logger = logging.getLogger(__name__)


def remove_search_index(dry_run=True):
    tag_query = Q()
    title_query = Q()
    for tag in DO_NOT_INDEX_LIST['tags']:
        tag_query |= Q(tags__name = tag)

    for title in DO_NOT_INDEX_LIST['titles']:
        title_query |= Q(title__contains = title)

    increment = 20
    nodes = paginated(AbstractNode, query=Q(is_public=True) & (tag_query | title_query), increment=increment, each=True)
    if dry_run:
        logger.warn('Dry run mode.')
        for node in nodes:
            logger.info('Removing {} with title \'{}\' from search index and SHARE.'.format(node._id, node.title))
    else:
        for node in nodes:
            update_node(node, bulk=False, async=True)
            update_node_share(node)

if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    init_app(routes=False)
    remove_search_index(dry_run=dry_run)
