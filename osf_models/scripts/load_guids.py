from website.app import init_app

init_app()

# LOAD GUIDS
from django.db import transaction
from framework.guid.model import Guid as MODMGuid
from osf_models.models import Guid
import gevent

guids = MODMGuid.find()
total = len(guids)
count = 0
page_size = 30000


def migrate_guid(guid):
    return Guid.objects.create(guid=guid)

while count < total:
    with transaction.atomic():
        threads = []
        for guid in guids[count:count + page_size].get_keys():
            threads.append(gevent.spawn(migrate_guid, guid))
            count += 1
            if count % page_size == 0:
                print count
        gevent.joinall(threads)
        print 'Committing {} through {}'.format(count - page_size, count)

print total
print count
