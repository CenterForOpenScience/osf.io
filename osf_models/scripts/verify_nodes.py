from website.models import Node as MODMNode
from website.models import Tag as MODMTag
from framework.auth import User as MODMUser
from modularodm import Q
from framework.guid.model import Guid as MODMGuid

from website.app import init_app
from osf_models.models import Node, User, Tag, Guid, Contributor


def verify_contributors(node, modm_node):
    for modm_contributor in modm_node.contributors:
        try:
            node.contributors.filter(_guid__guid=modm_contributor._id).exists()
        except Contributor.DoesNotExist:
            print 'Contributor {} exists in MODM but not in django on node {}'.format(modm_contributor._id,
                                                                                      node._guid.guid)

# find a way to make this use less ram or you're going to run out, cursors? they should be on by default
def main():
    nodes = Node.objects.all()
    for node in nodes:
        modm_node = MODMNode.load(node._guid.guid)
        verify_contributors(node, modm_node)
