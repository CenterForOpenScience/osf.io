"""
This will update node links on POPULAR_LINKS_NODE and NEW_AND_NOTEWORTHY_LINKS_NODE.
"""
import sys
import json
import urllib2
import logging
import datetime
import dateutil
import operator
from modularodm import Q
from website.app import init_app
from website import models
from framework.auth.core import Auth
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction
from website.settings.defaults import POPULAR_LINKS_NODE, NEW_AND_NOTEWORTHY_LINKS_NODE

logger = logging.getLogger(__name__)


def retrieve_data(url):
    """ Fetch data and decode json """
    response = urllib2.urlopen(url)
    data = json.load(response)
    return data


def get_popular_nodes():
    """ Fetch data from url that returns dict with a list of popular nodes from piwik """
    # TODO Change discover url to production url in production
    discover_url = 'http://127.0.0.1:5000/api/v1/explore/activity/popular/raw/'
    return retrieve_data(discover_url)


def get_new_and_noteworthy_nodes():
    """ Fetches nodes created in the last month and returns 25 sorted by log activity """
    # TODO Change discover url to production url
    today = datetime.datetime.now()
    last_month = (today - dateutil.relativedelta.relativedelta(months=1)).isoformat()
    discover_url = 'http://127.0.0.1:8000/v2/nodes/?sort=-date_created&page[size]=1000&related_counts=True&filter[date_created][gt]={}'.format(last_month)
    data = retrieve_data(discover_url)['data']
    node_log_count_mapping = {}
    for new_node in data:
        node_log_count_mapping[new_node['id']] = new_node['relationships']['logs']['links']['related']['meta']['count']
    sort_by_log_count = sorted(node_log_count_mapping.items(), key=operator.itemgetter(1), reverse=True)
    sorted_node_ids = [node[0] for node in sort_by_log_count]
    return sorted_node_ids[:25]


def update_node_links(designated_node, target_nodes, description):
    """ Takes designated node, removes current node links and replaces them with node links to target nodes """
    logger.warn('Repopulating {} with latest {} nodes.'.format(designated_node._id, description))
    user = designated_node.creator
    auth = Auth(user)

    for i in xrange(len(designated_node.nodes)-1, -1, -1):
        pointer = designated_node.nodes[i]
        designated_node.rm_pointer(pointer, auth)

    for n_id in target_nodes:
        if n_id != POPULAR_LINKS_NODE and n_id != NEW_AND_NOTEWORTHY_LINKS_NODE:
            n = models.Node.find(Q('_id', 'eq', n_id))[0]
            designated_node.add_pointer(n, auth, save=True)
            logger.info('Added node link to {}'.format(n))


def main(dry_run=True):
    init_app(routes=False)

    with TokuTransaction():
        # popular_nodes = get_popular_nodes()['popular_node_ids'] # TODO uncomment this
        popular_links_node = models.Node.find(Q('_id', 'eq', POPULAR_LINKS_NODE))[0]
        popular_nodes = ["md5v9", "pfvz4", "8pbtk", "a5wxn", "vt8d7"]  # TODO delete this
        new_and_noteworthy_links_node = models.Node.find(Q('_id', 'eq', NEW_AND_NOTEWORTHY_LINKS_NODE))[0]
        new_and_noteworthy_nodes = get_new_and_noteworthy_nodes()

        update_node_links(popular_links_node, popular_nodes, 'popular')
        update_node_links(new_and_noteworthy_links_node, new_and_noteworthy_nodes, 'new and noteworthy')

        if not dry_run:
            try:
                popular_links_node.save()
                logger.info('Node links on {} updated.'.format(popular_links_node._id))
            except:
                logger.error('Could not migrate popular nodes due to error')

            try:
                new_and_noteworthy_links_node.save()
                logger.info('Node links on {} updated.'.format(new_and_noteworthy_links_node._id))
            except:
                logger.error('Could not migrate new and noteworthy nodes due to error')


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)

