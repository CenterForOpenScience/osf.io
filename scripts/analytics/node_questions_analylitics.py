import logging
from django.db.models import Q
from osf.models import Node

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def node_question_numbers():

    nodes_with_descriptions = ~Q(description__exact='')
    nodes_without_descriptions = Q(description__exact='')

    nodes_with_wikis = Q(wikis__isnull=False)
    nodes_without_wikis = ~Q(wikis__isnull=False)

    nodes = Node.objects.filter(is_deleted=False)

    nodes_with_descriptions_and_with_wikis = nodes.filter(nodes_with_descriptions & nodes_with_wikis).distinct().count()
    logger.info('Number of nodes with descriptions and wikis: {}'.format(nodes_with_descriptions_and_with_wikis))

    nodes_without_descriptions_and_with_wikis = nodes.filter(nodes_without_descriptions & nodes_with_wikis).distinct().count()
    logger.info('Number of nodes without descriptions and with wikis: {}'.format(nodes_without_descriptions_and_with_wikis))

    nodes_with_descriptions_and_without_wikis = nodes.filter(nodes_with_descriptions & nodes_without_wikis).distinct().count()
    logger.info('Number of nodes with descriptions and without wikis: {}'.format(nodes_with_descriptions_and_without_wikis))

    nodes_without_descriptions_and_without_wikis = nodes.filter(nodes_without_descriptions & nodes_without_wikis).distinct().count()
    logger.info('Number of nodes without descriptions and without wikis: {}'.format(nodes_without_descriptions_and_without_wikis))

    # Sanity checksum
    total = nodes_without_descriptions_and_without_wikis + nodes_with_descriptions_and_without_wikis + nodes_without_descriptions_and_with_wikis + nodes_with_descriptions_and_with_wikis
    assert nodes.count() == total