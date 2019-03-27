# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from osf.models import Guid, OSFUser, AbstractNode, FileInfo
from addons.osfstorage.models import OsfStorageFileNode


def used_quota(user_id):
    guid = Guid.objects.get(
        _id=user_id,
        content_type_id=ContentType.objects.get_for_model(OSFUser).id
    )
    projects = AbstractNode.objects.filter(creator_id=guid.object_id).all()
    projects_ids = list(map(lambda p: p.id, projects))

    files = OsfStorageFileNode.objects.filter(
        target_object_id__in=projects_ids,
        target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
        deleted_on=None,
        deleted_by_id=None,
    ).all()
    files_ids = list(map(lambda f: f.id, files))

    db_sum = FileInfo.objects.filter(file_id__in=files_ids).aggregate(Sum('file_size'))
    return db_sum['file_size__sum']

def abbreviate_size(size):
    size = float(size)
    abbr_dict = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}

    power = 0
    while size > 1024 and power < 4:
        size /= 1024
        power += 1

    return (size, abbr_dict[power])
