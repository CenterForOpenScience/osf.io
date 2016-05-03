import gc

import pytz
from django.db import transaction
from osf_models.models import Node, NodeLog, User
from website.app import init_app
from website.models import Node as MODMNode
from website.models import NodeLog as MODMNodeLog

from .load_nodes import get_or_create_node, get_or_create_user


def main():
    # init_app()
    total = MODMNodeLog.find().count()
    # total = len(modm_nodelogs)
    count = 800000
    page_size = 100000
    django_nodelogs = []
    django_nodelogs_ids = []
    django_nodelogs_was_connected_to = {}

    # build a lookup table of all node_guids to node_pks
    nodes_lookup_table = {x['_guid__guid']: x['pk']
                          for x in Node.objects.all().values('_guid__guid',
                                                             'pk')}
    # build a lookup table of all user_guids to user_pks
    users_lookup_table = {x['_guid__guid']: x['pk']
                          for x in User.objects.all().values('_guid__guid',
                                                             'pk')}

    print 'Migrating {} logs...'.format(total)
    while count < total:
        modm_nodelogs = None
        modm_nodelogs = MODMNodeLog.find().sort('-date')[count:count + page_size]
        with transaction.atomic():
            print 'Migrating {} through {} which is {}'.format(
                count, count + page_size, len(modm_nodelogs))
            for modm_nodelog in modm_nodelogs:

                # don't recreate the log if it exists
                if NodeLog.objects.filter(guid=modm_nodelog._id).exists():
                    pass
                else:
                    if modm_nodelog.user is not None:
                        # try to get the pk out of the lookup table
                        user_pk = users_lookup_table.get(modm_nodelog.user._id,
                                                         None)

                        # it wasn't there
                        if user_pk is None:
                            # create a new user
                            user = get_or_create_user(modm_nodelog.user)
                            user_pk = user.pk
                            # put the user in the lookup table for next time
                            users_lookup_table[modm_nodelog.user._id] = user_pk
                    else:
                        # log doesn't have user
                        user_pk = None

                    # get the node (either a MODMNode instance or a node guid)
                    node_id = modm_nodelog.params.get(
                        'node', modm_nodelog.params.get('project'))
                    node_pk = None
                    if node_id is not None:
                        if isinstance(node_id, basestring):
                            # it's a guid, look it up in the table
                            node_pk = nodes_lookup_table.get(node_id, None)
                        elif isinstance(node_id, MODMNode):
                            # it's an instance, look it up in the table
                            node_pk = nodes_lookup_table.get(node_id._id, None)

                        if node_pk is None:
                            # it wasn't in the table
                            if isinstance(node_id, basestring):
                                # it's a guid, get an instance and create a PG version
                                modm_node = MODMNode.load(node_id)
                                django_node = get_or_create_node(modm_node)
                                if django_node is None:
                                    print 'Node {} does not exist.'.format(
                                        node_id)
                                    continue
                                node_pk = get_or_create_node(modm_node).pk
                                # put it in the table for later
                                nodes_lookup_table[modm_node._id] = node_pk
                            elif isinstance(node_id, MODMNode):
                                # it's an instance, create a PG version
                                node_pk = get_or_create_node(node_id).pk
                                # put it in the table for later
                                nodes_lookup_table[node_id._id] = node_pk
                    if node_pk is not None:
                        was_connected_to = []
                        for wct in modm_nodelog.was_connected_to:
                            wct_pk = nodes_lookup_table.get(wct._id, None)
                            if wct_pk is None:
                                wct_pk = get_or_create_node(wct).pk
                                nodes_lookup_table[wct._id] = wct_pk
                            was_connected_to.append(wct_pk)
                        if modm_nodelog.date is None:
                            nodelog_date = None
                        else:
                            nodelog_date = pytz.utc.localize(modm_nodelog.date)
                        if modm_nodelog._id not in django_nodelogs_ids:
                            django_nodelogs.append(NodeLog(
                                guid=modm_nodelog._id,
                                date=nodelog_date,
                                action=modm_nodelog.action,
                                params=modm_nodelog.params,
                                should_hide=modm_nodelog.should_hide,
                                user_id=user_pk,
                                foreign_user=modm_nodelog.foreign_user or '',
                                node_id=node_pk))
                            django_nodelogs_was_connected_to[
                                modm_nodelog._id] = was_connected_to
                            django_nodelogs_ids.append(modm_nodelog._id)
                        else:
                            print 'NodeLog with id {} and data {} was already in the bulk_create'.format(
                                modm_nodelog._id, modm_nodelog.to_storage())

                    else:
                        print 'Node {} is None on NodeLog {}...'.format(
                            node_id, modm_nodelog._id)
                count += 1
                if count % (page_size / 50) == 0:
                    print 'Through {}'.format(count)
                if count % page_size == 0:
                    print 'Starting to migrate {} through {} which should be {}'.format(
                        count - page_size, count, len(django_nodelogs))
                    if len(django_nodelogs) > 0:
                        NodeLog.objects.bulk_create(django_nodelogs)

                        print 'Finished migrating {} through {} which should be {}'.format(
                            count - page_size, count, len(django_nodelogs))
                        print 'Adding m2m values'
                        for django_nodelog in django_nodelogs:
                            nl = NodeLog.objects.get(guid=django_nodelog.guid)
                            nl.was_connected_to.add(
                                *django_nodelogs_was_connected_to[
                                    django_nodelog.guid])
                        print 'Finished adding m2m values'

                    django_nodelogs = []
                    django_nodelogs_was_connected_to = {}
                    garbage = gc.collect()
                    print 'Collected {} garbages!'.format(garbage)

    print 'Finished migration. MODM: {}, DJANGO: {}'.format(
        total, NodeLog.objects.all().count())
