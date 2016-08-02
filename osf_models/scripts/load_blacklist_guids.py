from __future__ import print_function
import gc

from framework.guid.model import BlacklistGuid
from osf_models.models import BlackListGuid

def main():
    odm_blacklist = BlacklistGuid.find()
    total = BlacklistGuid.find().count()
    count = 0
    page_size = 500000
    print('Migrating {} BlacklistGuids {}/batch'.format(total, page_size))

    django_blacklist_guids = []

    while count < total:
        blacklist_guids = odm_blacklist[count:count + page_size]
        for guid in blacklist_guids:
            django_blacklist_guids.append(BlackListGuid(guid=guid._id))
            count += 1
            if count % page_size == 0:
                print(count)

        print('Saving {} BlacklistGuids'.format(len(django_blacklist_guids)))
        BlackListGuid.objects.bulk_create(django_blacklist_guids)
        django_blacklist_guids = []
        blacklist_guids = []
        gc.collect()

    print('Django BlacklistGuids {}\nMODM BlacklistGuids {}'.format(BlackListGuid.objects.all().count(), total))
