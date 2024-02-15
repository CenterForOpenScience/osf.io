"""
This will update node links on POPULAR_LINKS_NODE and NEW_AND_NOTEWORTHY_LINKS_NODE.
"""
import sys
import logging
import dateutil

import django
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from website.app import init_app

from osf.models import Node, NodeLog
from framework.auth.core import Auth
from scripts import utils as script_utils
from framework.celery_tasks import app as celery_app
from framework.encryption import ensure_bytes
from website.settings import \
    POPULAR_LINKS_NODE, NEW_AND_NOTEWORTHY_LINKS_NODE,\
    NEW_AND_NOTEWORTHY_CONTRIBUTOR_BLACKLIST

logger = logging.getLogger(__name__)


def unique_contributors(nodes, node):
    """ Projects in New and Noteworthy should not have common contributors """

    for added_node in nodes:
        if set(added_node['contributors']).intersection(node['contributors']) != set():
            return False
    return True

def acceptable_title(node):
    """ Omit projects that have certain words in the title """

    omit_titles = ['test', 'photo', 'workshop', 'data']
    if any(word in node['title'].lower() for word in omit_titles):
        return False
    return True

def filter_nodes(node_list):
    final_node_list = []
    for node in node_list:
        if unique_contributors(final_node_list, node) and acceptable_title(node):
            final_node_list.append(node)
    return final_node_list

def get_new_and_noteworthy_nodes(noteworthy_links_node):
    """ Fetches new and noteworthy nodes

    Mainly: public top-level projects with the greatest number of unique log actions

    """
    today = timezone.now()
    last_month = (today - dateutil.relativedelta.relativedelta(months=1))
    data = Node.objects.filter(Q(created__gte=last_month) & Q(is_public=True) & Q(is_deleted=False)).get_roots()
    nodes = []
    for node in data:
        unique_actions = NodeLog.objects.filter(node=node.pk).order_by('action').distinct('action').count()
        n = {}
        n['unique_actions'] = unique_actions
        n['contributors'] = [c._id for c in node.contributors]
        n['_id'] = node._id
        n['title'] = node.title
        nodes.append(n)

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
            logger.info(f'Node {node._id} skipped because a contributor, {contrib._id}, is blacklisted.')
            return False

    return True

def update_node_links(designated_node, target_node_ids, description):
    """ Takes designated node, removes current node links and replaces them with node links to target nodes """
    logger.info(f'Repopulating {designated_node._id} with latest {description} nodes.')
    user = designated_node.creator
    auth = Auth(user)

    for pointer in designated_node.nodes_pointer:
        designated_node.rm_pointer(pointer, auth)

    for n_id in target_node_ids:
        n = Node.load(n_id)
        if is_eligible_node(n):
            designated_node.add_pointer(n, auth, save=True)
            logger.info(f'Added node link {n} to {designated_node}')

def main(dry_run=True):
    init_app(routes=False)

    new_and_noteworthy_links_node = Node.load(NEW_AND_NOTEWORTHY_LINKS_NODE)
    new_and_noteworthy_node_ids = get_new_and_noteworthy_nodes(new_and_noteworthy_links_node)

    update_node_links(new_and_noteworthy_links_node, new_and_noteworthy_node_ids, 'new and noteworthy')

    try:
        new_and_noteworthy_links_node.save()
        logger.info(f'Node links on {new_and_noteworthy_links_node._id} updated.')
    except (KeyError, RuntimeError) as error:
        logger.error('Could not migrate new and noteworthy nodes due to error')
        logger.exception(error)

    if dry_run:
        raise RuntimeError('Dry run -- transaction rolled back.')


@celery_app.task(name='scripts.populate_new_and_noteworthy_projects')
def run_main(dry_run=True):
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with transaction.atomic():
        main(dry_run=dry_run)

if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    django.setup()
    run_main(dry_run=dry_run)
