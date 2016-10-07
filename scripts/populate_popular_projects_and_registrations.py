"""
This will update node links on POPULAR_LINKS_NODE, POPULAR_LINKS_NODE_REGISTRATIONS and NEW_AND_NOTEWORTHY_LINKS_NODE.
"""
import sys
import logging
from modularodm import Q
from website.app import init_app
from website import models
from framework.auth.core import Auth
from scripts import utils as script_utils
from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction
from website.project.utils import activity
from website.settings import POPULAR_LINKS_NODE, POPULAR_LINKS_NODE_REGISTRATIONS

logger = logging.getLogger(__name__)

def popular_activity_json():
    """ Return popular_public_projects node_ids """

    activity_json = activity()
    popular_projects = activity_json['popular_public_projects']
    popular_registrations = activity_json['popular_public_registrations']

    return {
        'popular_public_projects': [proj._id for proj in popular_projects],
        'popular_public_registrations': [reg._id for reg in popular_registrations]
    }

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
    popular_activity = popular_activity_json()

    popular_node_ids = popular_activity['popular_node_ids']
    popular_links_node = models.Node.find_one(Q('_id', 'eq', POPULAR_LINKS_NODE))
    popular_registration_ids = popular_activity_json()['popular_registration_ids']
    popular_links_node_registrations = models.Node.find_one(Q('_id', 'eq', POPULAR_LINKS_NODE_REGISTRATIONS))

    update_node_links(popular_links_node, popular_node_ids, 'popular')
    update_node_links(popular_links_node_registrations, popular_registration_ids, 'popular registrations')

    try:
        popular_links_node.save()
        logger.info('Node links on {} updated.'.format(popular_links_node._id))
    except (KeyError, RuntimeError) as error:
        logger.error('Could not migrate popular nodes due to error')
        logger.exception(error)

    try:
        popular_links_node_registrations.save()
        logger.info('Node links for registrations on {} updated.'.format(popular_links_node._id))
    except (KeyError, RuntimeError) as error:
        logger.error('Could not migrate popular nodes for registrations due to error')
        logger.exception(error)

    if dry_run:
        raise RuntimeError('Dry run -- transaction rolled back.')


@celery_app.task(name='scripts.populate_popular_projects_and_registrations')
def run_main(dry_run=True):
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        main(dry_run=dry_run)

if __name__ == "__main__":
    dry_run = '--dry' in sys.argv
    run_main(dry_run=dry_run)
