import gc

import pytz
from osf_models.models import NodeLog
from website.app import init_app
from website.models import Node as MODMNode
from website.models import NodeLog as MODMNodeLog

from .load_nodes import get_or_create_node, get_or_create_user


def main():
    # init_app()
    modm_nodelogs = MODMNodeLog.find()
    total = len(modm_nodelogs)
    count = 0
    page_size = 10000
    django_nodelogs = []
    django_nodelogs_was_connected_to = {}

    print 'Migrating {} logs...'.format(total)
    while count < total:
        print 'Migrating {} through {}'.format(count, count + page_size)
        for modm_nodelog in modm_nodelogs[count:count + page_size]:
            user = get_or_create_user(modm_nodelog.user)
            node_id = modm_nodelog.params.get(
                'node', modm_nodelog.params.get('project'))

            if isinstance(node_id, basestring):
                modm_node = MODMNode.load(node_id)
            elif isinstance(node_id, MODMNodeLog):
                modm_node = node_id

            node = get_or_create_node(modm_node)
            if node is not None:
                was_connected_to = map(get_or_create_node,
                                       modm_nodelog.was_connected_to)
                if modm_nodelog.date is None:
                    nodelog_date = None
                else:
                    nodelog_date = pytz.utc.localize(modm_nodelog.date)
                django_nodelogs.append(
                    NodeLog(guid=modm_nodelog._id,
                            date=nodelog_date,
                            action=modm_nodelog.action,
                            params=modm_nodelog.params,
                            should_hide=modm_nodelog.should_hide,
                            user=user,
                            foreign_user=modm_nodelog.foreign_user or '',
                            node=node))
                django_nodelogs_was_connected_to[
                    modm_nodelog._id] = was_connected_to

            else:
                print 'Node {} is None on NodeLog {}...'.format(
                    node_id, modm_nodelog._id)
            count += 1
            if count % page_size == 0:
                print 'Starting to migrate {} through {} which should be {}'.format(
                    count - page_size, count, len(django_nodelogs))
                NodeLog.objects.bulk_create(django_nodelogs)

                print 'Finished migrating {} through {} which should be {}'.format(
                    count - page_size, count, len(django_nodelogs))
                print 'Adding m2m values'
                for django_nodelog in django_nodelogs:
                    nl = NodeLog.objects.get(guid=django_nodelog.guid)
                    for wct in django_nodelogs_was_connected_to[
                            django_nodelog.guid]:
                        nl.was_connected_to.add(wct)
                print 'Finished adding m2m values'

                django_nodelogs = []
                django_nodelogs_was_connected_to = {}
                garbage = gc.collect()
                print 'Collected {} garbages!'.format(garbage)

    print 'Finished migration. MODM: {}, DJANGO: {}'.format(
        total, NodeLog.objects.all().count())
