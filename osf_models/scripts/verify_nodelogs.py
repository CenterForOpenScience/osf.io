import gc

from framework.auth import User as MODMUser
from modularodm import Q
from osf_models.models import Node, NodeLog, User
from django.db import transaction

from website.models import Node as MODMNode
from website.models import NodeLog as MODMNodeLog
from osf_models.db.backends.postgresql_cursors.base import server_side_cursors
import pytz


def main():
    total = NodeLog.objects.all().count()
    count = 0
    page_size = 50000
    with transaction.atomic():
        qs = NodeLog.objects.all().order_by('-date').select_related('user').select_related('node').select_related('user___guid').select_related('node___guid')
        with server_side_cursors(qs, itersize=page_size):
            for log in qs.iterator():
                modm_nodelog = MODMNodeLog.load(log.guid)
                if modm_nodelog is not None:
                    modm_node = modm_nodelog.node
                    modm_user = modm_nodelog.user
                    if log.user is not None and log.user._guid.guid != modm_user._id:
                        print 'User doesn\'t match on log {}; {} != {}'.format(
                            log.guid, modm_user._id, log.user._guid.guid)
                    if log.node is not None and log.node._guid.guid != modm_nodelog.node._id:
                        print 'Node doesn\'t match on log {}; {} != {}'.format(
                            log.guid, modm_nodelog.node._id, log.node._guid.guid)
                    if log.date is not None and pytz.utc.localize(
                            modm_nodelog.date) != log.date:
                        print 'Date doesn\'t match on log {}'.format(log.guid)
                    if log.action is not None and log.action != modm_nodelog.action:
                        print 'Action doesn\'t match on log {}; `{}` != `{}`'.format(
                            log.guid, modm_nodelog.action, log.action)
                    if log.params is not None and log.params != modm_nodelog.params:
                        print 'Params doesn\'t match on log {}; `{}` != `{}`'.format(
                            log.guid, modm_nodelog.params, log.params)
                    if log.should_hide is not None and log.should_hide != modm_nodelog.should_hide:
                        print 'Should_hide does\'nt match on log {}; `{}` != `{}`'.format(
                            log.guid, modm_nodelog.should_hide, log.should_hide)
                    if log.foreign_user is not None and log.foreign_user != '' and log.foreign_user != modm_nodelog.foreign_user:
                        print 'Foreign_user doesn\'t match on log {}; `{}` != `{}`'.format(
                            log.guid, modm_nodelog.foreign_user, log.foreign_user)
                else:
                    print 'MODMNodeLog with id {} not found.'.format(log.guid)

                count += 1
                if count % page_size == 0:
                    MODMNodeLog._cache.clear()
                    MODMNodeLog._object_cache.clear()
                    print '{} through {}'.format(count, count + page_size)
