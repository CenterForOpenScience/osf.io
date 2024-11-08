from osf.models.preprint import Preprint
from osf.models.base import GuidVersionsThrough


def migrate_preprints_bulk():
    preprints_qs = Preprint.objects.all()
    vq_list = []
    batch_size = 500

    p_batch_list = [preprints_qs[x:x + batch_size] for x in range(0, preprints_qs.count(), batch_size)]

    for preprints_list in p_batch_list:
        for p in preprints_list:
            guid = p.guids.first()
            if not guid.versions.exists():
                vq_list.append(GuidVersionsThrough(object_id=p.id, version=0, content_type_id=129, quid_id=guid.id))

        GuidVersionsThrough.objects.bulk_create(vq_list)
        vq_list = []

    print('End')


def migrate_preprints_single():
    preprints_qs = Preprint.objects.all()

    for p in preprints_qs:
        guid = p.guids.first()

        if not guid.versions.exists():
            guid.versions.create(object_id=p.id, version=0, content_type_id=129)

    print('End')
