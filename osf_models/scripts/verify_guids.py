from website.app import init_app

init_app()

# VERIFY GUIDS
from framework.guid.model import Guid as MODMGuid
from osf_models.models import Guid

modm_guids = MODMGuid.find()
print 'MODM Guids: {}'.format(len(modm_guids))

guids = Guid.objects.filter(guid__in=modm_guids.get_keys())
filtered_count = len(guids)
total_count = Guid.objects.count()

if len(modm_guids) == filtered_count == total_count:
    print 'WINNING'
else:
    print 'LOSING'

print 'Postgres Guids: {}'.format(Guid.objects.count())
