from website.app import init_app

init_app()

# LOAD GUIDS
from framework.guid.model import Guid as MODMGuid
from osf_models.models import Guid

modm_guids = MODMGuid.find()
total = len(modm_guids)
count = 0
page_size = 10000

django_guids = []

for guid in modm_guids.get_keys():
    django_guids.append(Guid(guid=guid))
    count += 1
    if count % page_size == 0:
        print count

print 'saving {} guids'.format(count)

Guid.objects.bulk_create(django_guids)
print 'dun'

print total

print Guid.objects.all().count()
