# LOAD GUIDS
from framework.guid.model import Guid as MODMGuid
from osf_models.models import Guid

def main():
    modm_guids = MODMGuid.find()
    total = len(modm_guids)
    count = 0
    page_size = 10000
    print 'Migrating {} Guids'.format(total)

    django_guids = []

    for guid in modm_guids.get_keys():
        django_guids.append(Guid(guid=guid))
        count += 1
        if count % page_size == 0:
            print count

    print 'Saving {} Guids'.format(len(django_guids))

    Guid.objects.bulk_create(django_guids)

    print 'Django Guids {}\nMODM Guids {}'.format(Guid.objects.all().count(), total)

