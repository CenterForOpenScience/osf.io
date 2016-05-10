"""
This will update node links on POPULAR_LINKS_NODE and NEW_AND_NOTEWORTHY_LINKS_NODE.
"""
import sys
import logging
import datetime
import dateutil
from modularodm import Q
from website.app import init_app
from website import models
from framework.auth.core import Auth
from scripts import utils as script_utils
from framework.mongo import database as db
from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction
from website.discovery.views import activity
from website.settings import POPULAR_LINKS_NODE, NEW_AND_NOTEWORTHY_LINKS_NODE, NEW_AND_NOTEWORTHY_CONTRIBUTOR_BLACKLIST

logger = logging.getLogger(__name__)

def popular_activity_json():
    """ Return popular_public_projects node_ids """

    activity_json = activity()
    popular = activity_json['popular_public_projects']
    popular_ids = {'popular_node_ids': []}
    for project in popular:
        popular_ids['popular_node_ids'].append(project._id)
    return popular_ids

def unique_contributors(nodes, node):
    """ Projects in New and Noteworthy should not have common contributors """

    for added_node in nodes:
        if set(added_node['contributors']).intersection(node['contributors']) != set():
            return False
    return True

def acceptable_title(node):
    """ Omit projects that have certain words in the title """

    omit_titles = ['test', 'photo', 'workshop', 'data']
    if any(word in str(node['title']).lower() for word in omit_titles):
        return False
    return True

def filter_nodes(node_list):
    final_node_list = []
    for node in node_list:
        if unique_contributors(final_node_list, node) and acceptable_title(node):
            final_node_list.append(node)
    return final_node_list

def get_new_and_noteworthy_nodes():
    """ Fetches new and noteworthy nodes

    Mainly: public top-level projects with the greatest number of unique log actions

    """
    today = datetime.datetime.now()
    last_month = (today - dateutil.relativedelta.relativedelta(months=1))
    data = db.node.find({'date_created': {'$gt': last_month}, 'is_public': True, 'is_registration': False, 'parent_node': None,
                         'is_deleted': False, 'is_collection': False})
    nodes = []
    for node in data:
        unique_actions = len(db.nodelog.find({'node': node['_id']}).distinct('action'))
        node['unique_actions'] = unique_actions
        nodes.append(node)

    noteworthy_nodes = sorted(nodes, key=lambda node: node.get('unique_actions'), reverse=True)[:25]
    filtered_new_and_noteworthy = filter_nodes(noteworthy_nodes)

    return [each['_id'] for each in filtered_new_and_noteworthy]

def is_eligible_node(node):
    """
    Check to ensure that node is not the POPULAR or NEW_AND_NOTEWORTHY LINKS_NODE.
    Ensures no blacklisted contributor nodes are shown (for example, a test project created by QA)
    """
    if node._id == POPULAR_LINKS_NODE or node._id == NEW_AND_NOTEWORTHY_LINKS_NODE:
        return False

    for contrib in node.contributors:
        if contrib._id in NEW_AND_NOTEWORTHY_CONTRIBUTOR_BLACKLIST:
            logger.info('Node {} skipped because a contributor, {}, is blacklisted.'.format(node._id, contrib._id))
            return False

    return True

def update_node_links(designated_node, target_node_ids, description):
    """ Takes designated node, removes current node links and replaces them with node links to target nodes """
    logger.info('Repopulating {} with latest {} nodes.'.format(designated_node._id, description))
    user = designated_node.creator
    auth = Auth(user)

    for pointer in designated_node.nodes_pointer:
        designated_node.rm_pointer(pointer, auth)

    for n_id in target_node_ids:
        n = models.Node.load(n_id)
        if is_eligible_node(n):
            designated_node.add_pointer(n, auth, save=True)
            logger.info('Added node link {} to {}'.format(n, designated_node))

def main(dry_run=True):
    init_app(routes=False)

    popular_node_ids = popular_activity_json()['popular_node_ids']
    popular_links_node = models.Node.find_one(Q('_id', 'eq', POPULAR_LINKS_NODE))
    new_and_noteworthy_links_node = models.Node.find_one(Q('_id', 'eq', NEW_AND_NOTEWORTHY_LINKS_NODE))
    new_and_noteworthy_node_ids = get_new_and_noteworthy_nodes()

    update_node_links(popular_links_node, popular_node_ids, 'popular')
    update_node_links(new_and_noteworthy_links_node, new_and_noteworthy_node_ids, 'new and noteworthy')

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


@celery_app.task(name='scripts.populate_new_and_noteworthy_projects')
def run_main(dry_run=True):
    scripts_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        main(dry_run=dry_run)
