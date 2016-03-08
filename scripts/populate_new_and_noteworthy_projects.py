"""
This will update node links on POPULAR_LINKS_NODE and NEW_AND_NOTEWORTHY_LINKS_NODE.
"""
import sys
import logging
import datetime
import dateutil
import operator
import requests
from modularodm import Q
from website.app import init_app
from website import models
from framework.auth.core import Auth
from scripts import utils as script_utils
from framework.mongo import database as db
from framework.transactions.context import TokuTransaction
from website.project.model import Pointer
from website.settings import POPULAR_LINKS_NODE, NEW_AND_NOTEWORTHY_LINKS_NODE, NEW_AND_NOTEWORTHY_CONTRIBUTOR_BLACKLIST, DOMAIN

logger = logging.getLogger(__name__)

def retrieve_data(url):
    """ Fetch data and decode json """
    response = requests.get(url)
    data = response.json()
    return data

def get_popular_nodes():
    """ Fetch data from url that returns dict with a list of popular nodes from piwik """
    discover_url = DOMAIN + 'api/v1/explore/activity/popular/raw/'
    return retrieve_data(discover_url)

def get_new_and_noteworthy_nodes():
    """ Fetches nodes created in the last month and returns 25 sorted by highest log activity """
    today = datetime.datetime.now()
    last_month = (today - dateutil.relativedelta.relativedelta(months=1))
    data = db.node.find({'date_created': {'$gt': last_month}, 'is_public': True, 'is_registration': False})
    node_log_count_mapping = {}
    for new_node in data:
        node_log_count_mapping[new_node['_id']] = len(new_node['logs'])
    sort_by_log_count = sorted(node_log_count_mapping.items(), key=operator.itemgetter(1), reverse=True)
    sorted_node_ids = [node[0] for node in sort_by_log_count]
    return sorted_node_ids[:25]

def is_eligible_node(node):
    """
    Check to ensure that node is not the POPULAR or NEW_AND_NOTEWORTHY LINKS_NODE.
    Ensures QA members are not contributors
    """
    if node._id == POPULAR_LINKS_NODE or node._id == NEW_AND_NOTEWORTHY_LINKS_NODE:
        return False

    for contrib in node.contributors:
        if contrib._id in NEW_AND_NOTEWORTHY_CONTRIBUTOR_BLACKLIST:
            logger.info('Node {} skipped because a contributor, {}, is blacklisted.'.format(node._id, contrib._id))
            return False

    return True

def update_node_links(designated_node, target_nodes, description):
    """ Takes designated node, removes current node links and replaces them with node links to target nodes """
    logger.info('Repopulating {} with latest {} nodes.'.format(designated_node._id, description))
    user = designated_node.creator
    auth = Auth(user)

    for pointer in reversed(designated_node.nodes):
        if isinstance(pointer, Pointer):
            designated_node.rm_pointer(pointer, auth)

    for n_id in target_nodes:
        n = models.Node.find(Q('_id', 'eq', n_id))[0]
        if is_eligible_node(n):
            designated_node.add_pointer(n, auth, save=True)
            logger.info('Added node link {} to {}'.format(n, designated_node))

def main(dry_run=True):
    init_app(routes=False)

    popular_nodes = get_popular_nodes()['popular_node_ids']
    popular_links_node = models.Node.find(Q('_id', 'eq', POPULAR_LINKS_NODE))[0]
    new_and_noteworthy_links_node = models.Node.find(Q('_id', 'eq', NEW_AND_NOTEWORTHY_LINKS_NODE))[0]
    new_and_noteworthy_nodes = get_new_and_noteworthy_nodes()

    update_node_links(popular_links_node, popular_nodes, 'popular')
    update_node_links(new_and_noteworthy_links_node, new_and_noteworthy_nodes, 'new and noteworthy')

    try:
        popular_links_node.save()
        logger.info('Node links on {} updated.'.format(popular_links_node._id))
    except (KeyError, RuntimeError) as error:
        logger.error('Could not migrate popular nodes due to error')
        logger.exception(error)

    try:
        new_and_noteworthy_links_node.save()
        logger.info('Node links on {} updated.'.format(new_and_noteworthy_links_node._id))
    except (KeyError, RuntimeError) as error:
        logger.error('Could not migrate new and noteworthy nodes due to error')
        logger.exception(error)

    if dry_run:
        raise RuntimeError('Dry run -- transaction rolled back.')


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        main(dry_run=True)

