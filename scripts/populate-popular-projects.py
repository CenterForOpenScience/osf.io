"""
This will update node links on POPULAR_LINKS_NODE.
"""
import sys
import json
import urllib2
import logging
from modularodm import Q
from website.app import init_app
from website import models
from framework.auth.core import Auth
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction
from website.settings.defaults import POPULAR_LINKS_NODE

logger = logging.getLogger(__name__)

def get_popular_nodes():
    # TODO Change discover url to production url in production
    discover_url = 'http://127.0.0.1:5000/api/v1/explore/activity/popular/raw/'
    response = urllib2.urlopen(discover_url)
    data = json.load(response)
    return data

def main(dry_run=True):
    init_app(routes=False)

    with TokuTransaction():
        popular_node = models.Node.find(Q('_id', 'eq', POPULAR_LINKS_NODE))[0]
        logger.warn('Repopulating {} with latest popular nodes.'.format(popular_node._id))
        # popular_nodes = get_popular_nodes()['popular_node_ids'] # TODO uncomment this
        popular_nodes = ["njadc", "qgtvw", "bg9ha", "w4g8v", "bpuh9"]  # TODO delete this
        user = popular_node.creator
        auth = Auth(user)

        for i in xrange(len(popular_node.nodes)-1, -1, -1):
            pointer = popular_node.nodes[i]
            popular_node.rm_pointer(pointer, auth)
            logger.info('Removed node link to {}'.format(pointer.node._id))

        for n_id in popular_nodes:
            n = models.Node.find(Q('_id', 'eq', n_id))[0]
            popular_node.add_pointer(n, auth, save=True)
            logger.info('Added node link to {}'.format(n))

        if not dry_run:
            try:
                popular_node.save()
                logger.info('Popular nodes updated.')
            except:
                logger.error('Could not migrate popular nodes due to error')


if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)
