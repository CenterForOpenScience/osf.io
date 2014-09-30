"""

"""

import logging
import os
import sys
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir)
))

from modularodm.query.querydialect import DefaultQueryDialect as Q

from website.app import init_app
from website.models import Node


logger = logging.getLogger('root')

app = init_app('website.settings', set_backends=True, routes=True)


def copied_from_ancestor(node, attribute):
    parent = getattr(node, attribute)

    if (
        parent
        and parent.piwik_site_id is not None
        and parent.piwik_site_id == node.piwik_site_id
    ):
        return True

    if parent:
        copied_from_ancestor(parent, attribute)

    return False


print "=== Registrations ==="
for node in Node.find(Q('is_registration', 'eq', True)):
    if copied_from_ancestor(node, 'registered_from'):
        node.piwik_site_id = None
        node.save()
        print(node._id)


print "=== Forks ==="
for node in Node.find(Q('is_fork', 'eq', True)):
    if copied_from_ancestor(node, 'forked_from'):
        node.piwik_site_id = None
        node.save()
        print(node._id)