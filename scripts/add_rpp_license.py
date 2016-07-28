import logging
import sys

from website.app import init_app
from website.models import User, Node
from website.project.licenses import NodeLicense, ensure_licenses
from framework.auth import Auth

from modularodm import Q
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)

app = init_app()


def main(dry_run=False):
    if not dry_run:
        user = User.find_one(Q('_id', 'eq', 'cdi38'))
        node = Node.find_one(Q('_id', 'eq', 'ezcuj'))
        ensure_licenses()
        license_name = 'CC0 1.0 Universal'
        node_license = NodeLicense.find_one(
            Q('name', 'eq', license_name)
        )
        node.set_node_license(
                license_id=node_license.id,
                year='2016',
                copyright_holders='',
                auth=Auth(user)
        )
        node.save()
        logger.info("License '{}' has been added to project '{}' by user '{}'.".format(
                node_license.name, node._id, user._id))


if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)