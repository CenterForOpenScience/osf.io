# VERIFY GUIDS
from framework.guid.model import Guid as MODMGuid
from framework.guid.model import BlacklistGuid as MODMBlacklistGuid
from osf_models.models import BlackListGuid
from osf_models.models import Guid
import gc

def main():
    modm_guids = MODMGuid.find()
    print 'MODM Guids: {}'.format(len(modm_guids))

    guids = Guid.objects.filter(guid__in=modm_guids.get_keys())
    filtered_count = len(guids)
    total_count = Guid.objects.count()

    if len(modm_guids) == filtered_count == total_count:
        print 'Guids verified!'
    else:
        print 'Guids not verified!'

    print 'Postgres Guids: {}'.format(Guid.objects.count())

    guids = modm_guids = filtered_count = total_count = None
    gc.collect()

    modm_blacklist_guids = MODMBlacklistGuid.find()
    print 'MODM BlacklistGuids: {}'.format(len(modm_blacklist_guids))

    blacklist_guids = BlackListGuid.objects.filter(guid__in=modm_blacklist_guids.get_keys())
    filtered_count = len(blacklist_guids)
    total_count = BlackListGuid.objects.count()

    if len(modm_blacklist_guids) == filtered_count == total_count:
        print 'Blacklist Guids Verified!'
    else:
        print 'Blacklist Guids Not Verified!'

    print 'Postgres Blacklist Guids: {}'.format(BlackListGuid.objects.count())

    blacklist_guids = modm_blacklist_guids = filtered_count = total_count = None
    gc.collect()
