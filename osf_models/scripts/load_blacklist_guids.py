from website.app import init_app
init_app()

from django.db import transaction
from framework.guid.model import BlacklistGuid
from osf_models.models import BlackListGuid
import gevent

odm_blacklist = BlacklistGuid.find()
total = len(odm_blacklist)
count = 0
page_size = 30000


def migrate_blacklist_item(guid):
    pg_guid = BlackListGuid.objects.create(guid=guid._id)

while count < total:
    with transaction.atomic():
        page = odm_blacklist[count:count + page_size]
        threads = []
        for guid in page:
            threads.append(gevent.spawn(migrate_blacklist_item, guid))
            count += 1
        gevent.joinall(threads)
        print 'Committing {} through {}'.format(count - page_size, count)

print count
print total
