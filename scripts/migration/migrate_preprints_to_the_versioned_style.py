from django.apps import apps
from tqdm import tqdm
import time


def migrate_preprints_bulk():
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Preprint = apps.get_model('osf', 'Preprint')
    GuidVersionsThrough = apps.get_model('osf', 'GuidVersionsThrough')

    content_type_id = ContentType.objects.get_for_model(Preprint).id

    preprints_qs = Preprint.objects.all()
    vq_list = []
    batch_size = 500

    p_batch_list = [preprints_qs[x:x + batch_size] for x in range(1, preprints_qs.count(), batch_size)]

    for preprints_list in tqdm(p_batch_list, desc='Processing', unit='batch'):
        for p in tqdm(preprints_list, desc='Processing', unit='batch'):
            guid = p.guids.first()
            if not guid.versions.exists():
                vq_list.append(GuidVersionsThrough(object_id=p.id, version=1, content_type_id=content_type_id, quid_id=guid.id))

        GuidVersionsThrough.objects.bulk_create(vq_list)
        vq_list = []

    print('End')


def migrate_preprints_single():
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Preprint = apps.get_model('osf', 'Preprint')

    content_type_id = ContentType.objects.get_for_model(Preprint).id

    preprints_qs = Preprint.objects.all()
    for p in tqdm(preprints_qs):
        guid = p.guids.first()

        if not guid.versions.exists():
            guid.versions.create(object_id=p.id, version=1, content_type_id=content_type_id)

    print('End')
