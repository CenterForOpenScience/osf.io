from django.db.models import Prefetch

from django.contrib.contenttypes.models import ContentType
from osf.models import Guid, Preprint, GuidVersionsThrough


def main():
    content_type = ContentType.objects.get_for_model(Preprint)
    versions_queryset = GuidVersionsThrough.objects.order_by('-version')
    for guid in (
        Guid.objects.filter(content_type=content_type)
        .prefetch_related(Prefetch('versions', queryset=versions_queryset))
        .iterator(chunk_size=500)
    ):
        last_version: GuidVersionsThrough = guid.versions.first()
        last_version_object_id = last_version.object_id
        if guid.object_id != last_version_object_id:
            guid.object_id = last_version_object_id
            guid.referent = last_version.referent
        guid.save()


if __name__ == '__main__':
    main()
