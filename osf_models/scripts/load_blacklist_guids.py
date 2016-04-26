import gc

from django.db import transaction
from framework.guid.model import BlacklistGuid
from osf_models.models import BlackListGuid
from website.app import init_app

init_app()


odm_blacklist = BlacklistGuid.find()
total = len(odm_blacklist)
count = 0
page_size = 500000

django_blacklist_guids = []

while count < total:
    for guid in odm_blacklist[count:count+page_size]:
        django_blacklist_guids.append(BlackListGuid(guid=guid._id))
        count += 1
        if count % page_size == 0:
            print count

    print 'saving {} blacklist guids'.format(len(django_blacklist_guids))
    BlackListGuid.objects.bulk_create(django_blacklist_guids)
    django_blacklist_guids = []
    gc.collect()

print 'dun'

print total

print BlackListGuid.objects.all().count()
