import gc
from collections import deque
from datetime import datetime

import pytz
from django.db import transaction
from osf_models.models import NodeLog
from osf_models.scripts.migrate_nodes import build_pk_caches
from website.models import NodeLog as MODMNodeLog

global modm_to_django
modm_to_django = build_pk_caches()
print 'Cached {} MODM to django mappings...'.format(len(modm_to_django.keys()))


def main():
    start = datetime.now()
    split = start
    total = MODMNodeLog.find().count()

    count = 0
    page_size = 10000
    blank_users = 0
    blank_nodes = 0

    while count < total:
        garbage = gc.collect()
        print 'Collected {} whole garbages!'.format(garbage)
        print 'Migrating {} through {}'.format(count, count + page_size)

        django_nodelogs = deque()
        nodelog_guids = deque()

        for modm_nodelog in MODMNodeLog.find().sort('-date')[count:count +
                                                             page_size]:
            if modm_nodelog._id in nodelog_guids:
                print 'Nodelog with guid of {} and data of {} exists in batch'.format(
                    modm_nodelog._id, modm_nodelog.to_storage())
                continue
            else:
                nodelog_guids.append(modm_nodelog._id)

            try:
                user_pk = modm_to_django[modm_nodelog.user._id]
            except (KeyError, AttributeError) as ex:
                blank_users += 1
                user_pk = None

            try:
                node_pk = modm_to_django[getattr(modm_nodelog, 'node',
                                                 None)._id]
            except (KeyError, AttributeError) as ex:
                blank_nodes += 1
                print 'Found blank node on {}'.format(modm_nodelog._id)
                node_pk = None

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
                        user_id=user_pk,
                        foreign_user=modm_nodelog.foreign_user or '',
                        node_id=node_pk))

            count += 1
            if count % 1000 == 0:
                print 'Through {} in {}'.format(count, (
                    datetime.now() - split).total_seconds())
                split = datetime.now()
            if count % page_size == 0:
                print '{} blank users; {} blank nodes'.format(blank_users,
                                                              blank_nodes)
                print 'Starting to migrate {} through {} which is {}'.format(
                    count - page_size, count, len(django_nodelogs))
                splat = datetime.now()

                if len(django_nodelogs) > 0:
                    with transaction.atomic():
                        NodeLog.objects.bulk_create(django_nodelogs)

                print 'Finished migrating {} through {} in {} which is {}'.format(
                    count - page_size, count,
                    (datetime.now() - splat).total_seconds(),
                    len(django_nodelogs))

                django_nodelogs = deque()
                nodelog_guids = deque()

                garbage = gc.collect()
                print 'Collected {} whole garbages!'.format(garbage)

    print '\a\a\a\a\a'
    print 'Finished migration in {}. MODM: {}, DJANGO: {}'.format(
        (datetime.now() - start).total_seconds(), total,
        NodeLog.objects.count())
    print 'There were {} blank users and {} blank nodes'.format(blank_users,
                                                                blank_nodes)
