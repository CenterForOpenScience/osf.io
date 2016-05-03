import gc

from framework.auth import User as MODMUser
from modularodm import Q
from osf_models.models import Node, NodeLog, User
from website.app import init_app
from website.models import Node as MODMNode
from website.models import NodeLog as MODMNodeLog


def main():
    total = NodeLog.objects.all().count()
    count = 0
    page_size = 1000

    while count < total:
        for log in NodeLog.objects.all().order_by('-date')[count:count +
                                                           page_size]:
            print '{} through {}'.format(count, count + page_size)
            modm_nodelog = MODMNodeLog.load(log.guid)
            if modm_nodelog is not None:
                modm_node = modm_nodelog.node
                modm_user = modm_nodelog.user
                if log.user is not None and log.user._guid.guid != modm_user._id:
                    print 'User doesn\'t match on log {}'.format(log.guid)
                if log.node is not None and log.node._guid.guid != modm_nodelog.params.get(
                        'node', modm_nodelog.params.get('project')):
                    print 'Node doesn\'t match on log {}', format(log.guid)
            else:
                print 'MODMNodeLog with id {} not found.'.format(log.guid)
            count += 1
